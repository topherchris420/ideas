"""Command-line interface for the supported hello_os core package."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Iterable, Optional

from .core import (
    RotorDesign,
    available_materials,
    estimate_rotor_metrics,
    optimize_rotor,
    simulate_trace,
)


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
    metrics = estimate_rotor_metrics(design)
    trace = simulate_trace(design, duration_s=args.duration, samples=args.samples, rng=args.seed)

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

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("hello_os rotor explorer")
        print(_render_mapping(payload["design"]))
        print("\nDerived metrics")
        print(_render_mapping(payload["metrics"]))
        print("\nSynthetic trace")
        print(_render_mapping(payload["trace"]))
    return 0


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
