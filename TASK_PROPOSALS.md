# Development Backlog

The first professionalization pass created the supported `hello_os` package,
CLI, tests, and project metadata. Future work should continue in small,
test-backed increments.

## High-Value Follow-Ups

1. Add optional plotting helpers in a separate `hello_os.visualization` module.
   Keep imports lazy so the core package remains lightweight.

2. Build a notebook that consumes the package API instead of embedding large
   blocks of standalone code.

3. Add benchmark tests for `gravitomagnetic_field()` batch sizes once realistic
   target workloads are known.

4. Review the legacy archive section-by-section and promote only benign,
   reproducible experiments into maintained modules.

## Guardrails

- Do not import or execute the legacy archive as part of package startup.
- Do not add dependencies unless a supported module genuinely needs them.
- Every promoted experiment needs tests that import the real package surface.
