"""Public package surface for hello_os."""

from .core import (
    BOLTZMANN_CONSTANT,
    GRAVITATIONAL_CONSTANT,
    LIGHT_SPEED,
    MATERIALS,
    Material,
    OptimizationResult,
    RotorDesign,
    RotorMetrics,
    SignalTrace,
    angular_velocity_from_rpm,
    available_materials,
    classify_safety,
    estimate_integration_seconds,
    estimate_rotor_metrics,
    get_material,
    gravitomagnetic_field,
    optimize_rotor,
    quantum_noise,
    simulate_trace,
)
from .sweep import (
    SWEEPABLE_PARAMETERS,
    SensitivityResult,
    SweepResult,
    sensitivity_report,
    sweep_rotor,
)

# Visualization helpers are exported lazily (PEP 562) so importing hello_os
# stays lightweight and the renderers only load when actually used.
_VISUALIZATION_EXPORTS = frozenset(
    {"render_sweep_svg", "render_trace_svg", "save_svg"}
)

__all__ = [
    "BOLTZMANN_CONSTANT",
    "GRAVITATIONAL_CONSTANT",
    "LIGHT_SPEED",
    "MATERIALS",
    "Material",
    "OptimizationResult",
    "RotorDesign",
    "RotorMetrics",
    "SWEEPABLE_PARAMETERS",
    "SensitivityResult",
    "SignalTrace",
    "SweepResult",
    "angular_velocity_from_rpm",
    "available_materials",
    "classify_safety",
    "estimate_integration_seconds",
    "estimate_rotor_metrics",
    "get_material",
    "gravitomagnetic_field",
    "optimize_rotor",
    "quantum_noise",
    "render_sweep_svg",
    "render_trace_svg",
    "save_svg",
    "sensitivity_report",
    "simulate_trace",
    "sweep_rotor",
]


def __getattr__(name: str):
    if name in _VISUALIZATION_EXPORTS:
        from . import visualization

        return getattr(visualization, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
