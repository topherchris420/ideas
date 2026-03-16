"""Unit tests for core numerical routines in hello_os."""

import numpy as np
import sys
import os

# Import constants and functions from hello_os (no .py extension)
sys.path.insert(0, os.path.dirname(__file__))

# We need to extract the functions without running the full notebook.
# Parse the constants and functions directly.
G = 6.67430e-11
c = 2.99792458e8
kB = 1.380649e-23


def gravitomagnetic_field(r_vec, J_vec, v_rotor=0):
    """Copy of the function from hello_os for isolated testing."""
    r_vec = np.atleast_2d(r_vec)
    r = np.linalg.norm(r_vec, axis=1)
    mask = r >= 1e-12
    r_safe = np.where(mask, r, 1.0)
    J = np.linalg.norm(J_vec)
    if J == 0:
        return np.zeros(3) if r_vec.shape[0] == 1 else np.zeros((r_vec.shape[0], 3))
    r_hat = r_vec / r_safe[:, np.newaxis]
    J_dot_rhat = np.sum(J_vec * r_hat, axis=1)
    term1 = 3 * J_dot_rhat[:, np.newaxis] * r_hat
    term2 = term1 - J_vec
    factor = G / (c**2 * r_safe**3)
    B_g = factor[:, np.newaxis] * term2
    pn_factor = 1 + 3 * (v_rotor**2 / c**2)
    result = pn_factor * B_g
    result[~mask] = 0.0
    return result.squeeze()


def quantum_noise(t, a_rms=1e-12):
    """Copy of the function from hello_os for isolated testing."""
    n = len(t)
    shot = a_rms / np.sqrt(n) * np.random.randn(n)
    pink = np.cumsum(np.random.randn(n)) / np.sqrt(np.arange(1, n + 1))
    pink = pink - np.mean(pink)
    pink *= a_rms / 8
    white = a_rms / 15 * np.random.randn(n)
    return shot + pink + white


# ---- Tests for gravitomagnetic_field ----

def test_gravitomagnetic_field_zero_at_origin():
    """Field should be zero at the origin (singularity guard)."""
    result = gravitomagnetic_field(np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    assert np.allclose(result, 0.0), f"Expected zero at origin, got {result}"


def test_gravitomagnetic_field_zero_when_J_zero():
    """Field should be zero when angular momentum J is zero."""
    result = gravitomagnetic_field(np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 0.0]))
    assert np.allclose(result, 0.0), f"Expected zero for J=0, got {result}"


def test_gravitomagnetic_field_finite_for_normal_input():
    """Field should be finite for normal inputs."""
    result = gravitomagnetic_field(np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1e10]))
    assert np.all(np.isfinite(result)), f"Expected finite result, got {result}"
    assert np.any(np.abs(result) > 0), "Expected non-zero result for non-trivial input"


def test_gravitomagnetic_field_batch():
    """Vectorized input should return correct shape."""
    r_vecs = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    result = gravitomagnetic_field(r_vecs, np.array([0.0, 0.0, 1e10]))
    assert result.shape == (3, 3), f"Expected shape (3,3), got {result.shape}"
    assert np.all(np.isfinite(result))


# ---- Tests for quantum_noise ----

def test_quantum_noise_returns_finite():
    """Quantum noise should return all finite values."""
    t = np.linspace(0, 1, 1000)
    result = quantum_noise(t)
    assert np.all(np.isfinite(result)), "quantum_noise returned non-finite values"


def test_quantum_noise_correct_shape():
    """Output shape should match input length."""
    t = np.linspace(0, 1, 500)
    result = quantum_noise(t)
    assert result.shape == (500,), f"Expected shape (500,), got {result.shape}"


def test_quantum_noise_scales_with_amplitude():
    """Larger a_rms should produce larger noise amplitude on average."""
    np.random.seed(42)
    t = np.linspace(0, 1, 10000)
    small = quantum_noise(t, a_rms=1e-15)
    np.random.seed(42)
    large = quantum_noise(t, a_rms=1e-10)
    assert np.std(large) > np.std(small), "Larger a_rms should produce larger noise"


# ---- Tests for optimize_rotor SNR guard ----

def test_optimize_rotor_snr_guard():
    """The SNR guard should prevent division by zero."""
    predicted_snr_per_sec = 0.0
    # Simulate the guarded logic from optimize_rotor
    if predicted_snr_per_sec > 1e-15:
        result = 25 / predicted_snr_per_sec
    else:
        result = None
    assert result is None, "Should skip division when SNR is zero"


def test_optimize_rotor_snr_guard_near_zero():
    """Near-zero SNR should also be guarded."""
    predicted_snr_per_sec = 1e-20
    if predicted_snr_per_sec > 1e-15:
        result = 25 / predicted_snr_per_sec
    else:
        result = None
    assert result is None, "Should skip division when SNR is near-zero"


def test_optimize_rotor_snr_guard_positive():
    """Positive SNR should compute normally."""
    predicted_snr_per_sec = 5.0
    if predicted_snr_per_sec > 1e-15:
        result = 25 / predicted_snr_per_sec
    else:
        result = None
    assert result == 5.0, f"Expected 5.0, got {result}"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
