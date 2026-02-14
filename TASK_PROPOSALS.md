# Task Proposals from Quick Codebase Review

## 1) Typo fix task
**Task:** Fix the docstring typo/casing in `discover_patterns()` so the first sentence starts with a capitalized word ("Pattern discovery...").

**Why:** The function docstring currently starts with lowercase "pattern", which looks like a typo and reduces polish/readability.

## 2) Bug fix task
**Task:** Guard the `5σ detection` printout in `optimize_rotor()` against zero/near-zero SNR to prevent division by zero (`25 / predicted_snr_per_sec`).

**Why:** If `predicted_snr_per_sec` is `0` (or extremely close), the current code can crash or print misleading values.

## 3) Comment/documentation discrepancy task
**Task:** Resolve the discrepancy around `N` (number of rotors) in optimization: either enforce integer handling inside the objective/optimizer flow or update comments/docs to say it is optimized continuously then cast.

**Why:** The bounds comment says `Number of rotors (integer)`, but differential evolution optimizes continuous values unless explicitly constrained.

## 4) Test improvement task
**Task:** Add focused unit tests for numerical safety and invariants:
- `gravitomagnetic_field()` returns zero at origin and when `J_vec == 0`.
- `quantum_noise()` returns finite values with expected shape.
- `optimize_rotor()` reporting path handles zero/near-zero SNR without division errors.

**Why:** These are core numerical routines with edge-case logic, and currently there is no automated regression coverage.
