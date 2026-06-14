"""Safe, importable core models for the hello_os research playground."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Iterable, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

ArrayLike = Union[Sequence[float], np.ndarray]

GRAVITATIONAL_CONSTANT = 6.67430e-11
LIGHT_SPEED = 2.99792458e8
BOLTZMANN_CONSTANT = 1.380649e-23
SNR_EPSILON = 1e-15


@dataclass(frozen=True)
class Material:
    """Rotor material properties used by the supported gravitomagnetic model."""

    name: str
    density_kg_m3: float
    tensile_strength_pa: float
    color: str


MATERIALS: Mapping[str, Material] = {
    "Ti-6Al-4V": Material("Ti-6Al-4V", 4430.0, 900e6, "#4a90e2"),
    "Carbon Composite": Material("Carbon Composite", 1600.0, 1500e6, "#2ecc71"),
    "Beryllium": Material("Beryllium", 1850.0, 400e6, "#e74c3c"),
    "Maraging Steel": Material("Maraging Steel", 8000.0, 2400e6, "#9b59b6"),
    "Silicon Nitride": Material("Silicon Nitride", 3200.0, 3000e6, "#f1c40f"),
}


@dataclass(frozen=True)
class RotorDesign:
    """A complete rotor-array configuration."""

    mass_kg: float = 250.0
    radius_m: float = 0.7
    rpm: float = 28000.0
    shape_factor: float = 0.5
    rotor_count: int = 16
    array_radius_m: float = 2.5
    detector_distance_m: float = 1.3
    test_velocity_m_s: float = 1.0
    material_name: str = "Carbon Composite"
    noise_floor_m_s2: float = 1e-12

    def __post_init__(self) -> None:
        positive_fields = {
            "mass_kg": self.mass_kg,
            "radius_m": self.radius_m,
            "rpm": self.rpm,
            "rotor_count": self.rotor_count,
            "array_radius_m": self.array_radius_m,
            "detector_distance_m": self.detector_distance_m,
            "test_velocity_m_s": self.test_velocity_m_s,
            "noise_floor_m_s2": self.noise_floor_m_s2,
        }
        for name, value in positive_fields.items():
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive value")
        if not np.isfinite(self.shape_factor) or not 0 < self.shape_factor <= 1:
            raise ValueError("shape_factor must be in the interval (0, 1]")
        if int(self.rotor_count) != self.rotor_count:
            raise ValueError("rotor_count must be an integer")
        get_material(self.material_name)


@dataclass(frozen=True)
class RotorMetrics:
    """Derived performance and safety metrics for a rotor design."""

    material: Material
    angular_velocity_rad_s: float
    tip_speed_m_s: float
    single_rotor_angular_momentum: float
    total_angular_momentum: float
    max_safe_angular_velocity_rad_s: float
    stress_ratio: float
    safety_label: str
    safety_color: str
    field_at_detector_s_inv: float
    acceleration_peak_m_s2: float
    snr_per_second: float
    five_sigma_seconds: Optional[float]

    def as_dict(self) -> dict:
        data = asdict(self)
        data["material"] = asdict(self.material)
        return data


@dataclass(frozen=True)
class SignalTrace:
    """Synthetic detector trace for a rotor design."""

    time_s: np.ndarray
    signal_m_s2: np.ndarray
    noise_m_s2: np.ndarray
    trace_m_s2: np.ndarray
    metrics: RotorMetrics


@dataclass(frozen=True)
class OptimizationResult:
    """Result from the dependency-free rotor grid optimizer."""

    design: RotorDesign
    metrics: RotorMetrics
    candidates_evaluated: int
    max_stress_ratio: float

    def as_dict(self) -> dict:
        return {
            "design": asdict(self.design),
            "metrics": self.metrics.as_dict(),
            "candidates_evaluated": self.candidates_evaluated,
            "max_stress_ratio": self.max_stress_ratio,
        }


def available_materials() -> Tuple[str, ...]:
    """Return supported material names in display order."""

    return tuple(MATERIALS.keys())


def get_material(name: str) -> Material:
    """Return a material by exact or case-insensitive name."""

    if name in MATERIALS:
        return MATERIALS[name]

    normalized = name.casefold()
    for material_name, material in MATERIALS.items():
        if material_name.casefold() == normalized:
            return material

    valid = ", ".join(available_materials())
    raise ValueError(f"unknown material {name!r}; choose one of: {valid}")


def angular_velocity_from_rpm(rpm: float) -> float:
    """Convert revolutions per minute to radians per second."""

    if not np.isfinite(rpm) or rpm <= 0:
        raise ValueError("rpm must be a finite positive value")
    return float(rpm * 2 * np.pi / 60)


def estimate_integration_seconds(
    snr_per_second: float,
    threshold_sigma: float = 5.0,
    min_snr: float = SNR_EPSILON,
) -> Optional[float]:
    """Return integration time for a target sigma threshold, or None if SNR is tiny."""

    if not np.isfinite(snr_per_second) or snr_per_second <= min_snr:
        return None
    if not np.isfinite(threshold_sigma) or threshold_sigma <= 0:
        raise ValueError("threshold_sigma must be a finite positive value")
    return float((threshold_sigma / snr_per_second) ** 2)


def classify_safety(stress_ratio: float) -> Tuple[str, str]:
    """Map a rotor stress ratio to a display label and color."""

    if not np.isfinite(stress_ratio) or stress_ratio < 0:
        raise ValueError("stress_ratio must be finite and non-negative")
    if stress_ratio < 0.6:
        return "GOOD", "#00ff00"
    if stress_ratio < 0.85:
        return "CAUTION", "#ffff00"
    return "UNSAFE", "#ff0000"


def estimate_rotor_metrics(design: RotorDesign = RotorDesign()) -> RotorMetrics:
    """Compute safety, field, and detector metrics for a rotor design."""

    material = get_material(design.material_name)
    omega = angular_velocity_from_rpm(design.rpm)
    inertia = design.shape_factor * design.mass_kg * design.radius_m**2
    angular_momentum = inertia * omega
    total_angular_momentum = angular_momentum * design.rotor_count
    tip_speed = omega * design.radius_m

    omega_max = np.sqrt(
        material.tensile_strength_pa / (material.density_kg_m3 * design.radius_m**2 / 3)
    )
    stress_ratio = omega / omega_max
    safety_label, safety_color = classify_safety(stress_ratio)

    field = (
        GRAVITATIONAL_CONSTANT
        * total_angular_momentum
        / (LIGHT_SPEED**2 * design.detector_distance_m**3)
    )
    acceleration_peak = 4 * design.test_velocity_m_s * field
    snr_per_second = acceleration_peak / design.noise_floor_m_s2

    return RotorMetrics(
        material=material,
        angular_velocity_rad_s=float(omega),
        tip_speed_m_s=float(tip_speed),
        single_rotor_angular_momentum=float(angular_momentum),
        total_angular_momentum=float(total_angular_momentum),
        max_safe_angular_velocity_rad_s=float(omega_max),
        stress_ratio=float(stress_ratio),
        safety_label=safety_label,
        safety_color=safety_color,
        field_at_detector_s_inv=float(field),
        acceleration_peak_m_s2=float(acceleration_peak),
        snr_per_second=float(snr_per_second),
        five_sigma_seconds=estimate_integration_seconds(snr_per_second),
    )


def gravitomagnetic_field(
    r_vec: ArrayLike,
    j_vec: ArrayLike,
    v_rotor: float = 0.0,
    singularity_radius_m: float = 1e-12,
) -> np.ndarray:
    """Vectorized gravitomagnetic field approximation.

    Accepts one point shaped ``(3,)`` or a batch shaped ``(N, 3)``. Points inside
    ``singularity_radius_m`` return a zero field instead of producing infinities.
    """

    points, single_point = _as_points("r_vec", r_vec)
    angular_momentum = _as_vector3("j_vec", j_vec)
    if not np.isfinite(v_rotor) or v_rotor < 0:
        raise ValueError("v_rotor must be finite and non-negative")
    if not np.isfinite(singularity_radius_m) or singularity_radius_m <= 0:
        raise ValueError("singularity_radius_m must be finite and positive")

    result = np.zeros_like(points, dtype=float)
    if np.linalg.norm(angular_momentum) == 0:
        return result[0] if single_point else result

    radii = np.linalg.norm(points, axis=1)
    mask = radii >= singularity_radius_m
    if not np.any(mask):
        return result[0] if single_point else result

    safe_radii = np.where(mask, radii, 1.0)
    r_hat = points / safe_radii[:, np.newaxis]
    j_dot_rhat = np.sum(angular_momentum * r_hat, axis=1)
    field_shape = 3 * j_dot_rhat[:, np.newaxis] * r_hat - angular_momentum
    factor = GRAVITATIONAL_CONSTANT / (LIGHT_SPEED**2 * safe_radii**3)
    pn_factor = 1 + 3 * (v_rotor**2 / LIGHT_SPEED**2)

    result = pn_factor * factor[:, np.newaxis] * field_shape
    result[~mask] = 0.0
    return result[0] if single_point else result


def quantum_noise(
    t: ArrayLike,
    a_rms: float = 1e-12,
    rng: Optional[Union[int, np.random.Generator]] = None,
) -> np.ndarray:
    """Generate stable mixed shot, pink-like, and white noise for a time base."""

    time = _as_1d_array("t", t)
    if not np.isfinite(a_rms) or a_rms < 0:
        raise ValueError("a_rms must be finite and non-negative")

    n = len(time)
    if n == 0 or a_rms == 0:
        return np.zeros(n, dtype=float)

    generator = _coerce_rng(rng)
    shot = a_rms / np.sqrt(n) * generator.standard_normal(n)
    pink = np.cumsum(generator.standard_normal(n)) / np.sqrt(np.arange(1, n + 1))
    pink = pink - np.mean(pink)
    pink *= a_rms / 8
    white = a_rms / 15 * generator.standard_normal(n)
    return shot + pink + white


def simulate_trace(
    design: RotorDesign = RotorDesign(),
    duration_s: float = 20.0,
    samples: int = 1000,
    modulation_hz: float = 1.8,
    envelope_hz: float = 0.4,
    rng: Optional[Union[int, np.random.Generator]] = None,
) -> SignalTrace:
    """Create a deterministic-friendly synthetic detector trace."""

    if not np.isfinite(duration_s) or duration_s <= 0:
        raise ValueError("duration_s must be a finite positive value")
    if int(samples) != samples or samples < 2:
        raise ValueError("samples must be an integer >= 2")
    if not np.isfinite(modulation_hz) or modulation_hz <= 0:
        raise ValueError("modulation_hz must be a finite positive value")
    if not np.isfinite(envelope_hz) or envelope_hz <= 0:
        raise ValueError("envelope_hz must be a finite positive value")

    metrics = estimate_rotor_metrics(design)
    time = np.linspace(0, duration_s, int(samples))
    velocity_modulation = (
        design.test_velocity_m_s
        * np.sin(2 * np.pi * modulation_hz * time)
        * np.cos(2 * np.pi * envelope_hz * time)
    )
    signal = 4 * velocity_modulation * metrics.field_at_detector_s_inv
    noise = quantum_noise(time, a_rms=design.noise_floor_m_s2, rng=rng)
    return SignalTrace(
        time_s=time,
        signal_m_s2=signal,
        noise_m_s2=noise,
        trace_m_s2=signal + noise,
        metrics=metrics,
    )


def optimize_rotor(
    material_name: str = "Silicon Nitride",
    max_stress_ratio: float = 0.82,
    samples: int = 7,
    mass_range_kg: Tuple[float, float] = (100.0, 1500.0),
    radius_range_m: Tuple[float, float] = (0.3, 1.6),
    rpm_range: Tuple[float, float] = (8000.0, 60000.0),
    shape_factor_range: Tuple[float, float] = (0.35, 0.65),
    rotor_count_range: Tuple[int, int] = (1, 64),
) -> OptimizationResult:
    """Find a high-SNR rotor design with a deterministic bounded grid search."""

    if int(samples) != samples or samples < 2:
        raise ValueError("samples must be an integer >= 2")
    if not np.isfinite(max_stress_ratio) or max_stress_ratio <= 0:
        raise ValueError("max_stress_ratio must be finite and positive")

    get_material(material_name)
    masses = _linspace_range("mass_range_kg", mass_range_kg, int(samples))
    radii = _linspace_range("radius_range_m", radius_range_m, int(samples))
    rpms = _linspace_range("rpm_range", rpm_range, int(samples))
    shape_factors = _linspace_range("shape_factor_range", shape_factor_range, int(samples))
    rotor_counts = np.unique(
        np.rint(_linspace_range("rotor_count_range", rotor_count_range, int(samples))).astype(int)
    )

    best_design: Optional[RotorDesign] = None
    best_metrics: Optional[RotorMetrics] = None
    evaluated = 0

    for mass, radius, rpm, shape_factor, rotor_count in product(
        masses, radii, rpms, shape_factors, rotor_counts
    ):
        design = RotorDesign(
            mass_kg=float(mass),
            radius_m=float(radius),
            rpm=float(rpm),
            shape_factor=float(shape_factor),
            rotor_count=int(rotor_count),
            material_name=material_name,
        )
        metrics = estimate_rotor_metrics(design)
        evaluated += 1
        if metrics.stress_ratio > max_stress_ratio:
            continue
        if best_metrics is None or metrics.snr_per_second > best_metrics.snr_per_second:
            best_design = design
            best_metrics = metrics

    if best_design is None or best_metrics is None:
        raise RuntimeError("no rotor design satisfied the stress constraint")

    return OptimizationResult(
        design=best_design,
        metrics=best_metrics,
        candidates_evaluated=evaluated,
        max_stress_ratio=max_stress_ratio,
    )


def _as_1d_array(name: str, values: ArrayLike) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be a one-dimensional array")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values")
    return arr


def _as_vector3(name: str, values: ArrayLike) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.shape != (3,):
        raise ValueError(f"{name} must be shaped (3,)")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values")
    return arr


def _as_points(name: str, values: ArrayLike) -> Tuple[np.ndarray, bool]:
    arr = np.asarray(values, dtype=float)
    if arr.shape == (3,):
        points = arr.reshape(1, 3)
        single_point = True
    elif arr.ndim == 2 and arr.shape[1] == 3:
        points = arr
        single_point = False
    else:
        raise ValueError(f"{name} must be shaped (3,) or (N, 3)")

    if not np.all(np.isfinite(points)):
        raise ValueError(f"{name} must contain only finite values")
    return points, single_point


def _coerce_rng(rng: Optional[Union[int, np.random.Generator]]) -> np.random.Generator:
    if isinstance(rng, np.random.Generator):
        return rng
    return np.random.default_rng(rng)


def _linspace_range(name: str, values: Iterable[float], samples: int) -> np.ndarray:
    start, stop = tuple(values)
    if not np.isfinite(start) or not np.isfinite(stop) or start <= 0 or stop <= 0:
        raise ValueError(f"{name} must contain finite positive values")
    if stop < start:
        raise ValueError(f"{name} stop must be >= start")
    return np.linspace(float(start), float(stop), samples)
