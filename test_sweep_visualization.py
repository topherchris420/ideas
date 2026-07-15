"""Tests for the hello_os sweep, sensitivity, and SVG visualization modules."""

import json
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from hello_os import (
    SWEEPABLE_PARAMETERS,
    RotorDesign,
    render_sweep_svg,
    render_trace_svg,
    save_svg,
    sensitivity_report,
    simulate_trace,
    sweep_rotor,
)
from hello_os.cli import main


def _svg_elements(svg: str, tag: str):
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    return [element for element in root.iter() if element.tag.endswith(tag)]


def test_sweep_rpm_snr_scales_linearly():
    result = sweep_rotor("rpm", [10000.0, 20000.0, 40000.0])

    assert result.parameter == "rpm"
    assert result.values.shape == (3,)
    assert result.snr_per_second[1] == pytest.approx(2 * result.snr_per_second[0])
    assert result.snr_per_second[2] == pytest.approx(2 * result.snr_per_second[1])
    assert all(label in {"GOOD", "CAUTION", "UNSAFE"} for label in result.safety_labels)


def test_sweep_rotor_count_rounds_to_integers():
    result = sweep_rotor("rotor_count", [1.2, 7.6, 16.4])

    assert [design.rotor_count for design in result.designs] == [1, 8, 16]
    assert np.array_equal(result.values, [1.0, 8.0, 16.0])


def test_sweep_rejects_unknown_parameter():
    with pytest.raises(ValueError, match="unknown sweep parameter"):
        sweep_rotor("warp_factor", [1.0, 2.0])


def test_sweep_rejects_non_positive_values():
    with pytest.raises(ValueError, match="finite positive"):
        sweep_rotor("rpm", [10000.0, -5.0])


def test_best_safe_index_respects_stress_cap():
    result = sweep_rotor("rpm", np.linspace(5000, 40000, 8))
    best = result.best_safe_index(max_stress_ratio=0.82)

    safe = np.flatnonzero(result.stress_ratio <= 0.82)
    assert safe.size > 0
    assert best in safe
    assert result.snr_per_second[best] == pytest.approx(result.snr_per_second[safe].max())


def test_best_safe_index_returns_none_when_everything_is_unsafe():
    result = sweep_rotor("rpm", [55000.0, 60000.0])

    assert result.best_safe_index(max_stress_ratio=0.1) is None


def test_sensitivity_matches_known_power_laws():
    report = sensitivity_report(RotorDesign(rpm=12000))

    assert report.snr_elasticity["mass_kg"] == pytest.approx(1.0)
    assert report.snr_elasticity["radius_m"] == pytest.approx(2.0)
    assert report.snr_elasticity["rpm"] == pytest.approx(1.0)
    assert report.snr_elasticity["rotor_count"] == pytest.approx(1.0)
    assert report.snr_elasticity["detector_distance_m"] == pytest.approx(-3.0)
    assert report.snr_elasticity["noise_floor_m_s2"] == pytest.approx(-1.0)
    assert report.stress_elasticity["rpm"] == pytest.approx(1.0)
    assert report.stress_elasticity["radius_m"] == pytest.approx(1.0)
    assert report.stress_elasticity["mass_kg"] == pytest.approx(0.0, abs=1e-9)


def test_sensitivity_flags_inert_parameter():
    report = sensitivity_report(parameters=("array_radius_m",))

    assert report.snr_elasticity["array_radius_m"] == pytest.approx(0.0, abs=1e-12)
    assert report.stress_elasticity["array_radius_m"] == pytest.approx(0.0, abs=1e-12)


def test_sensitivity_handles_shape_factor_upper_bound():
    report = sensitivity_report(RotorDesign(shape_factor=1.0), parameters=("shape_factor",))

    assert report.snr_elasticity["shape_factor"] == pytest.approx(1.0)


def test_trace_svg_is_valid_xml_with_both_series():
    trace = simulate_trace(RotorDesign(rpm=12000), duration_s=1.0, samples=64, rng=3)
    svg = render_trace_svg(trace)

    assert svg.startswith("<svg")
    assert len(_svg_elements(svg, "polyline")) == 2


def test_sweep_svg_marks_every_point():
    result = sweep_rotor("rpm", np.linspace(9000, 30000, 6))
    svg = render_sweep_svg(result)

    assert len(_svg_elements(svg, "circle")) == 6
    assert len(_svg_elements(svg, "polyline")) == 1


def test_flat_sweep_still_renders():
    result = sweep_rotor("array_radius_m", [1.0, 2.0, 3.0])
    svg = render_sweep_svg(result)

    assert np.ptp(result.snr_per_second) == 0
    assert len(_svg_elements(svg, "circle")) == 3


def test_svg_titles_are_escaped():
    trace = simulate_trace(samples=16, duration_s=1.0, rng=1)
    svg = render_trace_svg(trace, title="a <b> & 'c'")

    assert "<b>" not in svg
    assert len(_svg_elements(svg, "text")) > 0


def test_save_svg_round_trips(tmp_path):
    trace = simulate_trace(samples=16, duration_s=1.0, rng=1)
    target = save_svg(render_trace_svg(trace), tmp_path / "trace.svg")

    assert target.exists()
    assert target.read_text(encoding="utf-8").startswith("<svg")


def test_save_svg_rejects_non_svg_content(tmp_path):
    with pytest.raises(ValueError, match="rendered SVG"):
        save_svg("just text", tmp_path / "bad.svg")


def test_cli_sweep_emits_json_payload(capsys):
    exit_code = main(
        [
            "--sweep",
            "rpm",
            "--sweep-start",
            "10000",
            "--sweep-stop",
            "20000",
            "--sweep-points",
            "5",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["parameter"] == "rpm"
    assert len(payload["values"]) == 5
    assert len(payload["safety_labels"]) == 5
    assert "best_safe_index" in payload


def test_cli_sweep_requires_a_range():
    with pytest.raises(SystemExit):
        main(["--sweep", "rpm"])


def test_cli_sensitivity_json_covers_all_parameters(capsys):
    exit_code = main(["--sensitivity", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert set(payload["snr_elasticity"]) == set(SWEEPABLE_PARAMETERS)


def test_cli_writes_trace_svg(tmp_path, capsys):
    target = tmp_path / "trace.svg"
    exit_code = main(
        ["--json", "--samples", "16", "--duration", "1", "--svg", str(target)]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["svg_path"] == str(target)
    assert target.read_text(encoding="utf-8").startswith("<svg")


def test_cli_writes_sweep_svg(tmp_path, capsys):
    target = tmp_path / "sweep.svg"
    exit_code = main(
        [
            "--sweep",
            "rpm",
            "--sweep-start",
            "9000",
            "--sweep-stop",
            "30000",
            "--sweep-points",
            "4",
            "--svg",
            str(target),
        ]
    )

    capsys.readouterr()
    assert exit_code == 0
    assert len(_svg_elements(target.read_text(encoding="utf-8"), "circle")) == 4
