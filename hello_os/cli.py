"""Command-line interface for the supported hello_os core package."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Iterable, Optional

import numpy as np

from .core import (
    RotorDesign,
    available_materials,
    estimate_rotor_metrics,
    optimize_rotor,
    simulate_trace,
)
from .sweep import SWEEPABLE_PARAMETERS, sensitivity_report, sweep_rotor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hello-os",
        description="Explore safe hello_os rotor metrics and synthetic detector traces.",
    )
    parser.add_argument("--list-materials", action="store_true", help="show supported materials")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--optimize", action="store_true", help="run deterministic rotor optimization")
    parser.add_argument("--optimizer-samples", type=int, default=7, help="grid samples per dimension")
    parser.add_argument("--mass", type=float, default=250.0, help="rotor mass in kg")
    parser.add_argument("--radius", type=float, default=0.7, help="rotor radius in meters")
    parser.add_argument("--rpm", type=float, default=28000.0, help="rotor speed")
    parser.add_argument("--shape-factor", type=float, default=0.5, help="moment of inertia factor")
    parser.add_argument("--rotors", type=int, default=16, help="number of rotors")
    parser.add_argument("--array-radius", type=float, default=2.5, help="array radius in meters")
    parser.add_argument("--distance", type=float, default=1.3, help="detector distance in meters")
    parser.add_argument("--test-velocity", type=float, default=1.0, help="test velocity in m/s")
    parser.add_argument("--material", default="Carbon Composite", help="material name")
    parser.add_argument("--duration", type=float, default=20.0, help="trace duration in seconds")
    parser.add_argument("--samples", type=int, default=1000, help="trace sample count")
    parser.add_argument("--seed", type=int, default=42, help="random seed for synthetic trace")
    parser.add_argument(
        "--sweep",
        choices=SWEEPABLE_PARAMETERS,
        help="sweep one design parameter across a range",
    )
    parser.add_argument("--sweep-start", type=float, help="first swept value")
    parser.add_argument("--sweep-stop", type=float, help="last swept value")
    parser.add_argument("--sweep-points", type=int, default=15, help="number of sweep points")
    parser.add_argument(
        "--sensitivity",
        action="store_true",
        help="report how strongly each parameter drives SNR and stress",
    )
    parser.add_argument(
        "--svg",
        metavar="PATH",
        help="write a dependency-free SVG chart of the sweep or trace",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.list_materials:
        for material in available_materials():
            print(material)
        return 0

    if args.optimize:
        result = optimize_rotor(
            material_name=args.material,
            samples=args.optimizer_samples,
        )
        if args.json:
            print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        else:
            print("hello_os optimized rotor design")
            print(_render_mapping(asdict(result.design)))
            print("\nDerived metrics")
            print(_render_mapping(result.metrics.as_dict()))
        return 0

    design = RotorDesign(
        mass_kg=args.mass,
        radius_m=args.radius,
        rpm=args.rpm,
        shape_factor=args.shape_factor,
        rotor_count=args.rotors,
        array_radius_m=args.array_radius,
        detector_distance_m=args.distance,
        test_velocity_m_s=args.test_velocity,
        material_name=args.material,
    )

    if args.sweep:
        if args.sweep_start is None or args.sweep_stop is None:
            parser.error("--sweep requires --sweep-start and --sweep-stop")
        values = np.linspace(args.sweep_start, args.sweep_stop, args.sweep_points)
        result = sweep_rotor(args.sweep, values, design=design)
        best = result.best_safe_index()
        if args.svg:
            _write_svg(args.svg, sweep=result)

        payload = result.as_dict()
        payload["best_safe_index"] = best
        payload["best_safe_design"] = asdict(result.designs[best]) if best is not None else None
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"hello_os parameter sweep: {args.sweep}")
            for index in range(len(result.values)):
                print(
                    f"  {_format(float(result.values[index]))}: "
                    f"snr={_format(float(result.snr_per_second[index]))} "
                    f"stress={_format(float(result.stress_ratio[index]))} "
                    f"safety={result.safety_labels[index]}"
                )
            if best is None:
                print("no swept design satisfied the stress constraint")
            else:
                print(
                    f"best safe candidate: {args.sweep}="
                    f"{_format(float(result.values[best]))} "
                    f"snr={_format(float(result.snr_per_second[best]))}"
                )
            if args.svg:
                print(f"wrote sweep chart to {args.svg}")
        return 0

    if args.sensitivity:
        report = sensitivity_report(design)
        if args.json:
            print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        else:
            print("hello_os sensitivity report (log-log elasticities)")
            for parameter in report.snr_elasticity:
                print(
                    f"  {parameter}: snr={_format(report.snr_elasticity[parameter])} "
                    f"stress={_format(report.stress_elasticity[parameter])}"
                )
        return 0

    metrics = estimate_rotor_metrics(design)
    trace = simulate_trace(design, duration_s=args.duration, samples=args.samples, rng=args.seed)
    if args.svg:
        _write_svg(args.svg, trace=trace)

    payload = {
        "design": asdict(design),
        "metrics": metrics.as_dict(),
        "trace": {
            "duration_s": float(trace.time_s[-1] - trace.time_s[0]),
            "samples": int(len(trace.time_s)),
            "signal_peak_m_s2": float(abs(trace.signal_m_s2).max()),
            "trace_std_m_s2": float(trace.trace_m_s2.std()),
        },
    }
    if args.svg:
        payload["svg_path"] = args.svg

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("hello_os rotor explorer")
        print(_render_mapping(payload["design"]))
        print("\nDerived metrics")
        print(_render_mapping(payload["metrics"]))
        print("\nSynthetic trace")
        print(_render_mapping(payload["trace"]))
        if args.svg:
            print(f"\nwrote trace chart to {args.svg}")
    return 0


def _write_svg(path: str, trace=None, sweep=None) -> None:
    from .visualization import render_sweep_svg, render_trace_svg, save_svg

    svg = render_sweep_svg(sweep) if sweep is not None else render_trace_svg(trace)
    save_svg(svg, path)


def _render_mapping(values: dict) -> str:
    lines = []
    for key, value in values.items():
        if isinstance(value, dict):
            lines.append(f"  {key}:")
            lines.extend(f"    {inner_key}: {_format(inner_value)}" for inner_key, inner_value in value.items())
        else:
            lines.append(f"  {key}: {_format(value)}")
    return "\n".join(lines)


def _format(value: object) -> str:
    if value is None:
        return "not reachable at current SNR"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
