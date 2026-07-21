# hello_os

`hello_os` is a compact, importable Python package for exploring safe
gravitomagnetic rotor-array toy models, synthetic detector traces, and
configuration-driven optimization.

The repository now separates supported code from the original Colab export:

- `hello_os/` contains the maintained Python package and CLI.
- `test_hello_os.py` exercises the real package surface.
- `explainer/` holds an animated explainer video for the model.
- `legacy/hello_os_colab_export.txt` preserves the raw notebook export as
  reference material only. It is intentionally not imported or auto-executed.

## Explainer Video

A six-scene animated explainer walks through the idea, the materials, the safety
model, and the detector trace — all driven by the same numbers the package
computes.

[![hello_os animated explainer](explainer/hello_os-explainer.gif)](explainer/)

Its data (materials, the safe-tip-speed formula, and the seeded detector trace)
mirrors `hello_os/core.py`, so the story stays true to the code. The clip above
is a rendered capture of the full 34.5-second animation; see
[`explainer/`](explainer/) for the interactive source (with live color/material
tweaks) and instructions to run it locally.

## Install

```bash
python -m pip install -e ".[dev]"
```

The supported package depends on NumPy. The development extra installs pytest
for the test suite.

## Use The CLI

```bash
python -m hello_os --json
python -m hello_os --material "Silicon Nitride" --rpm 32000 --rotors 24
python -m hello_os --optimize --optimizer-samples 5 --json
python -m hello_os --list-materials
python -m hello_os --sweep rpm --sweep-start 8000 --sweep-stop 36000 --sweep-points 8
python -m hello_os --sensitivity --json
python -m hello_os --svg trace.svg
```

The CLI emits either readable text or JSON for downstream notebooks, dashboards,
and automation. `--sweep` varies one design parameter across a range and reports
the best candidate that stays within the stress constraint. `--sensitivity`
prints log-log elasticities showing how strongly each parameter drives SNR and
rotor stress. `--svg PATH` writes a dependency-free SVG chart of the sweep (or,
without `--sweep`, the synthetic trace).

## Use The API

```python
from hello_os import RotorDesign, estimate_rotor_metrics, simulate_trace

design = RotorDesign(
    material_name="Carbon Composite",
    mass_kg=250,
    radius_m=0.7,
    rpm=28_000,
    rotor_count=16,
)

metrics = estimate_rotor_metrics(design)
trace = simulate_trace(design, samples=1000, rng=42)

print(metrics.safety_label)
print(metrics.snr_per_second)
print(trace.trace_m_s2.shape)
```

### Sweeps, Sensitivity, And Charts

```python
import numpy as np
from hello_os import render_sweep_svg, save_svg, sensitivity_report, sweep_rotor

sweep = sweep_rotor("rpm", np.linspace(8000, 36000, 8), design=design)
best = sweep.best_safe_index()          # highest SNR within the stress budget
save_svg(render_sweep_svg(sweep), "sweep.svg")

report = sensitivity_report(design)
print(report.snr_elasticity["detector_distance_m"])   # -3.0: SNR ~ 1/d^3
```

`sweep_rotor` evaluates metrics along one design axis; `sensitivity_report`
computes local log-log elasticities, so power-law scalings come out exact
(SNR scales as `rpm**1`, `radius_m**2`, `detector_distance_m**-3`, ...).
The SVG renderers in `hello_os.visualization` use only the standard library —
no matplotlib dependency — and are loaded lazily, so `import hello_os` stays
lightweight.

## Quality Checks

```bash
python -m py_compile hello_os/*.py
python -m pytest -q
```

Before opening a pull request, run the checks above for any files you touched.
The tests are designed to catch numerical edge cases, shape regressions, and CLI
output drift.

## Design Notes

- The package is import-safe: importing `hello_os` does not start plots,
  installers, network calls, GPU setup, or long simulations.
- Numerical routines validate shapes and finite values before computing.
- Synthetic noise accepts a seed or `numpy.random.Generator` for reproducible
  experiments.
- The optimizer is a bounded deterministic grid search, so it works without
  SciPy and is predictable in CI.
