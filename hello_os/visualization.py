"""Dependency-free SVG charts for hello_os traces and sweeps.

The backlog called for plotting helpers without weighing down the core
package. Instead of an optional matplotlib dependency, these renderers emit
standalone SVG documents using only the standard library and NumPy, so they
run anywhere the package imports — including CI — and the output drops
straight into notebooks, dashboards, and READMEs.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import List, Sequence, Tuple, Union

import numpy as np

from .core import SignalTrace
from .sweep import SweepResult

_MARGIN_LEFT = 78.0
_MARGIN_RIGHT = 24.0
_MARGIN_TOP = 46.0
_MARGIN_BOTTOM = 52.0
_TICK_COUNT = 5

_SIGNAL_COLOR = "#1f77b4"
_TRACE_COLOR = "#b0b0b0"
_GRID_COLOR = "#e3e3e3"
_TEXT_COLOR = "#333333"


def render_trace_svg(
    trace: SignalTrace,
    width: int = 880,
    height: int = 340,
    title: str = "hello_os synthetic detector trace",
) -> str:
    """Render a signal trace as a standalone SVG string."""

    if not isinstance(trace, SignalTrace):
        raise TypeError("trace must be a hello_os SignalTrace")
    frame = _PlotFrame(
        width,
        height,
        x_domain=_padded_domain(trace.time_s),
        y_domain=_padded_domain(np.concatenate([trace.trace_m_s2, trace.signal_m_s2])),
    )

    body = frame.axes(title=title, x_label="time (s)", y_label="acceleration (m/s^2)")
    body.append(frame.polyline(trace.time_s, trace.trace_m_s2, _TRACE_COLOR, 1.0))
    body.append(frame.polyline(trace.time_s, trace.signal_m_s2, _SIGNAL_COLOR, 2.0))
    body.append(
        frame.legend(
            [("signal", _SIGNAL_COLOR), ("signal + noise", _TRACE_COLOR)]
        )
    )
    return frame.document(body)


def render_sweep_svg(
    sweep: SweepResult,
    width: int = 880,
    height: int = 340,
    title: str = "",
) -> str:
    """Render a parameter sweep as a standalone SVG string.

    Marker fill uses each design's safety color, so unsafe regions of the
    sweep are visible at a glance.
    """

    if not isinstance(sweep, SweepResult):
        raise TypeError("sweep must be a hello_os SweepResult")
    frame = _PlotFrame(
        width,
        height,
        x_domain=_padded_domain(sweep.values),
        y_domain=_padded_domain(sweep.snr_per_second),
    )

    body = frame.axes(
        title=title or f"hello_os sweep: {sweep.parameter}",
        x_label=sweep.parameter,
        y_label="SNR per second",
    )
    body.append(frame.polyline(sweep.values, sweep.snr_per_second, _SIGNAL_COLOR, 2.0))
    for value, snr, metrics in zip(sweep.values, sweep.snr_per_second, sweep.metrics):
        body.append(frame.marker(value, snr, metrics.safety_color))
    body.append(frame.legend([("marker fill = safety rating", _TEXT_COLOR)]))
    return frame.document(body)


def save_svg(svg: str, path: Union[str, Path]) -> Path:
    """Write an SVG string to disk and return the resolved path."""

    if not isinstance(svg, str) or not svg.lstrip().startswith("<svg"):
        raise ValueError("svg must be a rendered SVG string")
    target = Path(path)
    target.write_text(svg, encoding="utf-8")
    return target


def _padded_domain(values: np.ndarray) -> Tuple[float, float]:
    """Return a (low, high) domain, padded so flat data still has extent."""

    arr = np.asarray(values, dtype=float)
    low = float(arr.min())
    high = float(arr.max())
    if low == high:
        pad = max(abs(low), 1.0) * 0.5
        return low - pad, high + pad
    return low, high


class _PlotFrame:
    """Maps data coordinates onto an SVG pixel frame and emits primitives."""

    def __init__(
        self,
        width: int,
        height: int,
        x_domain: Tuple[float, float],
        y_domain: Tuple[float, float],
    ) -> None:
        if width < 240 or height < 160:
            raise ValueError("width must be >= 240 and height >= 160")
        self.width = float(width)
        self.height = float(height)
        self.x_low, self.x_high = x_domain
        self.y_low, self.y_high = y_domain
        self.plot_left = _MARGIN_LEFT
        self.plot_right = self.width - _MARGIN_RIGHT
        self.plot_top = _MARGIN_TOP
        self.plot_bottom = self.height - _MARGIN_BOTTOM

    def x(self, value: float) -> float:
        span = self.x_high - self.x_low
        fraction = (value - self.x_low) / span
        return self.plot_left + fraction * (self.plot_right - self.plot_left)

    def y(self, value: float) -> float:
        span = self.y_high - self.y_low
        fraction = (value - self.y_low) / span
        return self.plot_bottom - fraction * (self.plot_bottom - self.plot_top)

    def axes(self, title: str, x_label: str, y_label: str) -> List[str]:
        parts = [
            f'<rect x="0" y="0" width="{self.width:g}" height="{self.height:g}" fill="#ffffff"/>',
            f'<text x="{self.width / 2:g}" y="24" text-anchor="middle" '
            f'font-size="15" font-weight="bold" fill="{_TEXT_COLOR}">{escape(title)}</text>',
        ]
        for tick in np.linspace(self.x_low, self.x_high, _TICK_COUNT):
            px = self.x(tick)
            parts.append(
                f'<line x1="{px:.2f}" y1="{self.plot_top:g}" x2="{px:.2f}" '
                f'y2="{self.plot_bottom:g}" stroke="{_GRID_COLOR}" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{px:.2f}" y="{self.plot_bottom + 18:g}" text-anchor="middle" '
                f'font-size="11" fill="{_TEXT_COLOR}">{_format_tick(tick)}</text>'
            )
        for tick in np.linspace(self.y_low, self.y_high, _TICK_COUNT):
            py = self.y(tick)
            parts.append(
                f'<line x1="{self.plot_left:g}" y1="{py:.2f}" x2="{self.plot_right:g}" '
                f'y2="{py:.2f}" stroke="{_GRID_COLOR}" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{self.plot_left - 8:g}" y="{py + 4:.2f}" text-anchor="end" '
                f'font-size="11" fill="{_TEXT_COLOR}">{_format_tick(tick)}</text>'
            )
        parts.append(
            f'<rect x="{self.plot_left:g}" y="{self.plot_top:g}" '
            f'width="{self.plot_right - self.plot_left:g}" '
            f'height="{self.plot_bottom - self.plot_top:g}" '
            f'fill="none" stroke="{_TEXT_COLOR}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{(self.plot_left + self.plot_right) / 2:g}" '
            f'y="{self.height - 12:g}" text-anchor="middle" font-size="12" '
            f'fill="{_TEXT_COLOR}">{escape(x_label)}</text>'
        )
        parts.append(
            f'<text x="18" y="{(self.plot_top + self.plot_bottom) / 2:g}" '
            f'text-anchor="middle" font-size="12" fill="{_TEXT_COLOR}" '
            f'transform="rotate(-90 18 {(self.plot_top + self.plot_bottom) / 2:g})">'
            f"{escape(y_label)}</text>"
        )
        return parts

    def polyline(
        self, xs: np.ndarray, ys: np.ndarray, color: str, stroke_width: float
    ) -> str:
        points = " ".join(
            f"{self.x(float(px)):.2f},{self.y(float(py)):.2f}" for px, py in zip(xs, ys)
        )
        return (
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke_width:g}" stroke-linejoin="round"/>'
        )

    def marker(self, x_value: float, y_value: float, fill: str) -> str:
        return (
            f'<circle cx="{self.x(float(x_value)):.2f}" cy="{self.y(float(y_value)):.2f}" '
            f'r="4" fill="{fill}" stroke="{_TEXT_COLOR}" stroke-width="1"/>'
        )

    def legend(self, entries: Sequence[Tuple[str, str]]) -> str:
        parts = []
        y_offset = self.plot_top + 16
        for label, color in entries:
            parts.append(
                f'<text x="{self.plot_right - 10:g}" y="{y_offset:g}" text-anchor="end" '
                f'font-size="11" fill="{color}">{escape(label)}</text>'
            )
            y_offset += 15
        return "".join(parts)

    def document(self, body: Sequence[str]) -> str:
        content = "\n  ".join(body)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width:g}" '
            f'height="{self.height:g}" viewBox="0 0 {self.width:g} {self.height:g}" '
            f'role="img">\n  {content}\n</svg>\n'
        )


def _format_tick(value: float) -> str:
    return f"{value:.4g}"
