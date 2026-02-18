## 2025-05-15 - Redundant Correlation Calculation
**Learning:** In simulation loops involving agent-based models (like `hello_os`), recomputing statistical moments (mean, std) inside $O(N^2)$ inner loops is a massive performance killer. Pre-normalization outside the loop transforms the complexity from $O(N^2 \cdot W)$ full correlations to $O(N^2 \cdot W)$ simple dot products, but reduces the constant factor by ~7x.
**Action:** Always look for opportunities to hoist invariant calculations (like vector normalization) out of nested loops, especially in correlation-heavy workloads.
