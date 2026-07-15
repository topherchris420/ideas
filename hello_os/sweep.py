"""Deterministic parameter sweeps and local sensitivity analysis.

These helpers turn the static single-design metrics in :mod:`hello_os.core`
into dynamic explorations: sweep one design parameter across a range, or
measure how strongly each parameter drives SNR and rotor stress. Everything
is NumPy-only, deterministic, and safe to run in CI.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Mapping, Optional, Tuple

import numpy as np

from .core import (
    ArrayLike,
    RotorDesign,
    RotorMetrics,
    estimate_rotor_metrics,
)

SWEEPABLE_PARAMETERS: Tuple[str, ...] = (
    "mass_kg",
    "radius_m",
    "rpm",
    "shape_factor",
    "rotor_count",
    "array_radius_m",
    "detector_distance_m",
    "test_velocity_m_s",
    "noise_floor_m_s2",
)


@dataclass(frozen=True)
class SweepResult:
    """Metrics evaluated along one swept design parameter."""

    parameter: str
    values: np.ndarray
    snr_per_second: np.ndarray
    stress_ratio: np.ndarray
    safety_labels: Tuple[str, ...]
    five_sigma_seconds: Tuple[Optional[float], ...]
    designs: Tuple[RotorDesign, ...]
    metrics: Tuple[RotorMetrics, ...]

    def best_safe_index(self, max_stress_ratio: float = 0.82) -> Optional[int]:
        """Return the index with the highest SNR whose stress stays bounded."""

        if not np.isfinite(max_stress_ratio) or max_stress_ratio <= 0:
            raise ValueError("max_stress_ratio must be finite and positive")
        safe = np.flatnonzero(self.stress_ratio <= max_stress_ratio)
        if safe.size == 0:
            return None
        return int(safe[np.argmax(self.snr_per_second[safe])])

    def as_dict(self) -> dict:
        return {
            "parameter": self.parameter,
            "values": [float(v) for v in self.values],
            "snr_per_second": [float(v) for v in self.snr_per_second],
            "stress_ratio": [float(v) for v in self.stress_ratio],
            "safety_labels": list(self.safety_labels),
            "five_sigma_seconds": list(self.five_sigma_seconds),
        }


@dataclass(frozen=True)
class SensitivityResult:
    """Local log-log sensitivities (elasticities) around a base design.

    An elasticity of ``k`` for a parameter means the metric locally scales as
    ``parameter ** k``: SNR doubles when an elasticity-1 parameter doubles.
    """

    design: RotorDesign
    relative_step: float
    snr_elasticity: Mapping[str, float]
    stress_elasticity: Mapping[str, float]

    def as_dict(self) -> dict:
        return {
            "design": asdict(self.design),
            "relative_step": self.relative_step,
            "snr_elasticity": dict(self.snr_elasticity),
            "stress_elasticity": dict(self.stress_elasticity),
        }


def sweep_rotor(
    parameter: str,
    values: ArrayLike,
    design: RotorDesign = RotorDesign(),
) -> SweepResult:
    """Evaluate rotor metrics while varying a single design parameter.

    ``rotor_count`` values are rounded to the nearest integer before use; all
    other parameters are swept as floats. Values must be finite and positive.
    """

    if parameter not in SWEEPABLE_PARAMETERS:
        valid = ", ".join(SWEEPABLE_PARAMETERS)
        raise ValueError(f"unknown sweep parameter {parameter!r}; choose one of: {valid}")

    points = np.asarray(values, dtype=float)
    if points.ndim != 1 or points.size == 0:
        raise ValueError("values must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(points)) or np.any(points <= 0):
        raise ValueError("values must contain only finite positive numbers")
    if parameter == "rotor_count":
        points = np.rint(points)
        if np.any(points < 1):
            raise ValueError("rotor_count values must round to at least 1")

    designs = []
    metrics = []
    for point in points:
        applied = int(point) if parameter == "rotor_count" else float(point)
        candidate = replace(design, **{parameter: applied})
        designs.append(candidate)
        metrics.append(estimate_rotor_metrics(candidate))

    return SweepResult(
        parameter=parameter,
        values=points,
        snr_per_second=np.array([m.snr_per_second for m in metrics]),
        stress_ratio=np.array([m.stress_ratio for m in metrics]),
        safety_labels=tuple(m.safety_label for m in metrics),
        five_sigma_seconds=tuple(m.five_sigma_seconds for m in metrics),
        designs=tuple(designs),
        metrics=tuple(metrics),
    )


def sensitivity_report(
    design: RotorDesign = RotorDesign(),
    relative_step: float = 1e-3,
    parameters: Optional[Tuple[str, ...]] = None,
) -> SensitivityResult:
    """Estimate log-log derivatives of SNR and stress for each parameter.

    Uses a central difference in log space, which is exact for the power-law
    scalings that dominate this model. ``rotor_count`` is perturbed by whole
    units; ``shape_factor`` falls back to a one-sided step at its upper bound.
    """

    if not np.isfinite(relative_step) or not 0 < relative_step < 0.5:
        raise ValueError("relative_step must be in the interval (0, 0.5)")

    chosen = SWEEPABLE_PARAMETERS if parameters is None else parameters
    snr_elasticity = {}
    stress_elasticity = {}
    for parameter in chosen:
        if parameter not in SWEEPABLE_PARAMETERS:
            valid = ", ".join(SWEEPABLE_PARAMETERS)
            raise ValueError(
                f"unknown sensitivity parameter {parameter!r}; choose one of: {valid}"
            )
        low, high = _perturbed_values(design, parameter, relative_step)
        metrics_low = _metrics_at(design, parameter, low)
        metrics_high = _metrics_at(design, parameter, high)
        log_span = math.log(high) - math.log(low)
        snr_elasticity[parameter] = (
            math.log(metrics_high.snr_per_second) - math.log(metrics_low.snr_per_second)
        ) / log_span
        stress_elasticity[parameter] = (
            math.log(metrics_high.stress_ratio) - math.log(metrics_low.stress_ratio)
        ) / log_span

    return SensitivityResult(
        design=design,
        relative_step=float(relative_step),
        snr_elasticity=snr_elasticity,
        stress_elasticity=stress_elasticity,
    )


def _perturbed_values(
    design: RotorDesign, parameter: str, relative_step: float
) -> Tuple[float, float]:
    base = float(getattr(design, parameter))
    if parameter == "rotor_count":
        low = base - 1 if base > 1 else base
        return low, base + 1
    low = base * (1.0 - relative_step)
    high = base * (1.0 + relative_step)
    if parameter == "shape_factor" and high > 1.0:
        high = base
    return low, high


def _metrics_at(design: RotorDesign, parameter: str, value: float) -> RotorMetrics:
    applied = int(value) if parameter == "rotor_count" else value
    return estimate_rotor_metrics(replace(design, **{parameter: applied}))
