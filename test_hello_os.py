"""Tests for the supported hello_os package surface."""

import json

import numpy as np
import pytest

from hello_os import (
    RotorDesign,
    available_materials,
    estimate_integration_seconds,
    estimate_rotor_metrics,
    gravitomagnetic_field,
    optimize_rotor,
    quantum_noise,
    simulate_trace,
)
from hello_os.cli import main


def test_gravitomagnetic_field_zero_at_origin():
    result = gravitomagnetic_field(
        np.array([0.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
    )

    assert result.shape == (3,)
    assert np.allclose(result, 0.0)


def test_gravitomagnetic_field_zero_when_angular_momentum_is_zero():
    result = gravitomagnetic_field(
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 0.0, 0.0]),
    )

    assert np.allclose(result, 0.0)


def test_gravitomagnetic_field_vectorized_batch_is_finite():
    points = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )

    result = gravitomagnetic_field(points, np.array([0.0, 0.0, 1e10]))

    assert result.shape == (3, 3)
    assert np.all(np.isfinite(result))


def test_gravitomagnetic_field_rejects_bad_shapes():
    with pytest.raises(ValueError, match="shaped"):
        gravitomagnetic_field(np.array([1.0, 2.0]), np.array([0.0, 0.0, 1.0]))


def test_quantum_noise_is_reproducible_with_seed():
    t = np.linspace(0, 1, 500)

    first = quantum_noise(t, rng=123)
    second = quantum_noise(t, rng=123)

    assert first.shape == (500,)
    assert np.all(np.isfinite(first))
    assert np.allclose(first, second)


def test_quantum_noise_zero_amplitude_returns_zero_trace():
    t = np.linspace(0, 1, 12)

    result = quantum_noise(t, a_rms=0.0, rng=123)

    assert np.array_equal(result, np.zeros(12))


def test_integration_time_guard_handles_zero_and_near_zero_snr():
    assert estimate_integration_seconds(0.0) is None
    assert estimate_integration_seconds(1e-20) is None
    assert estimate_integration_seconds(5.0) == pytest.approx(1.0)


def test_rotor_metrics_are_dynamic_and_bounded():
    low_rpm = estimate_rotor_metrics(RotorDesign(rpm=10000))
    high_rpm = estimate_rotor_metrics(RotorDesign(rpm=20000))

    assert available_materials()
    assert high_rpm.tip_speed_m_s == pytest.approx(2 * low_rpm.tip_speed_m_s)
    assert high_rpm.total_angular_momentum == pytest.approx(
        2 * low_rpm.total_angular_momentum
    )
    assert high_rpm.snr_per_second > low_rpm.snr_per_second
    assert high_rpm.safety_label in {"GOOD", "CAUTION", "UNSAFE"}


def test_simulate_trace_returns_matching_arrays():
    trace = simulate_trace(RotorDesign(rpm=12000), duration_s=2.0, samples=128, rng=7)

    assert trace.time_s.shape == (128,)
    assert trace.signal_m_s2.shape == (128,)
    assert trace.noise_m_s2.shape == (128,)
    assert trace.trace_m_s2.shape == (128,)
    assert np.all(np.isfinite(trace.trace_m_s2))


def test_optimizer_respects_stress_constraint():
    result = optimize_rotor(samples=3, max_stress_ratio=0.82)

    assert result.candidates_evaluated > 0
    assert result.metrics.stress_ratio <= 0.82
    assert result.metrics.snr_per_second > 0


def test_cli_json_outputs_machine_readable_payload(capsys):
    exit_code = main(["--json", "--samples", "16", "--duration", "1", "--seed", "5"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["design"]["material_name"] == "Carbon Composite"
    assert payload["metrics"]["safety_label"] in {"GOOD", "CAUTION", "UNSAFE"}
    assert payload["trace"]["samples"] == 16
