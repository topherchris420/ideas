# Development Backlog

The first professionalization pass created the supported `hello_os` package,
CLI, tests, and project metadata. Future work should continue in small,
test-backed increments.

## Completed

- `hello_os.visualization` now ships dependency-free SVG renderers for traces
  and sweeps (no matplotlib required), exported lazily from the package root.
- `hello_os.sweep` adds deterministic parameter sweeps (`sweep_rotor`) and
  local log-log sensitivity analysis (`sensitivity_report`), wired into the
  CLI via `--sweep`, `--sensitivity`, and `--svg`.

## High-Value Follow-Ups

1. Build a notebook that consumes the package API instead of embedding large
   blocks of standalone code. The new sweep + SVG helpers make good material.

2. Add benchmark tests for `gravitomagnetic_field()` batch sizes once realistic
   target workloads are known.

3. Review the legacy archive section-by-section and promote only benign,
   reproducible experiments into maintained modules.

4. Consider an optional matplotlib backend behind the same visualization API
   for interactive use; keep the SVG path as the zero-dependency default.

## Guardrails

- Do not import or execute the legacy archive as part of package startup.
- Do not add dependencies unless a supported module genuinely needs them.
- Every promoted experiment needs tests that import the real package surface.
