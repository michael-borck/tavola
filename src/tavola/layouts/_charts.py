"""Shared chart data and HTML fragments for chart layouts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tavola.brief import Claim, Series
from tavola.layouts._parts import esc, proportion_claims

if TYPE_CHECKING:
    from tavola.layouts.base import LayoutContext


@dataclass(frozen=True)
class ChartModel:
    claims: list[Claim]
    values: list[float]
    total: float
    denominator: float
    share_mode: bool
    title: str
    kicker: str
    note: str


def build_chart(ctx: LayoutContext) -> ChartModel:
    claims = [
        claim for claim in proportion_claims(ctx) if claim.numeric is not None
    ][:4]
    values = [abs(claim.numeric or 0.0) for claim in claims]
    total = sum(values)
    relationship = ctx.relationship("proportion")
    percent = bool(claims) and all(claim.unit == "%" for claim in claims)
    share_mode = relationship is not None or (percent and 90 <= total <= 110)
    if share_mode:
        title = relationship.summary if relationship else "Share of the whole"
        kicker = "Share"
        note = "Bar length is each value’s share of the total."
        denominator = total
    else:
        title = "Relative scale"
        kicker = "Bars"
        note = "Bar length is relative to the largest value."
        denominator = max(values) if values else 0.0
    return ChartModel(
        claims=claims,
        values=values,
        total=total,
        denominator=denominator,
        share_mode=share_mode,
        title=title,
        kicker=kicker,
        note=note,
    )


def bar_rows(model: ChartModel) -> str:
    rows = []
    for index, (claim, value) in enumerate(
        zip(model.claims, model.values, strict=True), start=1
    ):
        width = max(0.0, min(100.0, value / model.denominator * 100))
        rows.append(
            '<li class="bar-row">'
            '<div class="bar-meta">'
            f'<span class="bar-label">{esc(claim.label or claim.text)}</span>'
            f'<span class="bar-value">{esc(claim.value)}</span>'
            "</div>"
            '<div class="bar-track">'
            f'<span class="bar-fill bar-fill-{index}" style="width: {width:.1f}%"></span>'
            "</div>"
            "</li>"
        )
    return "".join(rows)


def donut_figure(model: ChartModel) -> str:
    segments = []
    offset = 0.0
    for index, value in enumerate(model.values, start=1):
        share = max(0.0, min(100.0, value / model.denominator * 100))
        segments.append(
            f'<circle class="donut-seg donut-seg-{index}" cx="21" cy="21" r="15.9155" '
            'pathLength="100" '
            f'stroke-dasharray="{share:.2f} {100 - share:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" />'
        )
        offset += share
    units = {claim.unit for claim in model.claims}
    if units == {"%"}:
        center, center_label = "100%", "share"
    elif len(units) == 1 and None not in units:
        center, center_label = _fmt(model.total), str(next(iter(units)))
    else:
        center, center_label = str(len(model.claims)), "parts"
    return (
        '<div class="donut-figure">'
        '<svg class="donut-svg" viewBox="0 0 42 42" role="img" '
        f'aria-label="{esc(model.title)}">'
        '<circle class="donut-track" cx="21" cy="21" r="15.9155" pathLength="100" />'
        f'<g transform="rotate(-90 21 21)">{"".join(segments)}</g>'
        "</svg>"
        '<div class="donut-center">'
        f"<strong>{center}</strong><span>{center_label}</span>"
        "</div>"
        "</div>"
    )


def donut_legend(model: ChartModel) -> str:
    rows = []
    for index, claim in enumerate(model.claims, start=1):
        rows.append(
            '<li class="donut-legend-row">'
            f'<span class="donut-swatch donut-swatch-{index}"></span>'
            f'<span class="donut-legend-label">{esc(claim.label or claim.text)}</span>'
            f'<span class="donut-value">{esc(claim.value)}</span>'
            "</li>"
        )
    return f'<ul class="donut-legend">{"".join(rows)}</ul>'


def _fmt(value: float) -> str:
    return f"{value:,.1f}".removesuffix(".0")


def trend_range(series: Sequence[Series]) -> tuple[float, float]:
    values = [value for item in series for value in item.values]
    return min(values), max(values)


def trend_figure(series_list: Sequence[Series]) -> str:
    series = list(series_list)
    low, high = trend_range(series)
    span = high - low or 1.0
    left, right, top, bottom = 4.0, 96.0, 5.0, 38.0
    blocks = []
    dots = []
    for series_index, item in enumerate(series, start=1):
        step = (right - left) / max(1, len(item.values) - 1)
        points = []
        for index, value in enumerate(item.values):
            x = left + step * index
            y = bottom - (value - low) / span * (bottom - top)
            points.append((x, y))
        polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        suffix = f" trend-line-{series_index}" if series_index > 1 else ""
        if series_index == 1:
            area = (
                f"M {points[0][0]:.2f} 40 "
                + " ".join(f"L {x:.2f} {y:.2f}" for x, y in points)
                + f" L {points[-1][0]:.2f} 40 Z"
            )
            blocks.append(f'<path class="trend-area" d="{area}" />')
        blocks.append(
            f'<polyline class="trend-line{suffix}" points="{polyline}" />'
        )
        dot_class = "trend-dot" + (
            f" trend-dot-series-{series_index}" if series_index > 1 else ""
        )
        dots.append(
            "".join(
                f'<span class="{dot_class}{" trend-dot-last" if index == len(points) - 1 else ""}" '
                f'style="left: {x:.2f}%; top: {y / 44 * 100:.2f}%"></span>'
                for index, (x, y) in enumerate(points)
            )
        )
    grid = "".join(
        f'<line x1="4" x2="96" y1="{y}" y2="{y}" />'
        for y in (top, (top + bottom) / 2, bottom)
    )
    x_labels = "".join(f"<span>{esc(label)}</span>" for label in series[0].labels)
    legend = ""
    if len(series) > 1:
        legend = '<div class="trend-legend">' + "".join(
            f'<span><i class="trend-swatch-{index}"></i>{esc(item.name)}</span>'
            for index, item in enumerate(series, start=1)
        ) + "</div>"
    return (
        '<div class="trend-figure">'
        '<div class="trend-plot">'
        '<div class="trend-canvas">'
        '<svg class="trend-svg" viewBox="0 0 100 44" '
        'preserveAspectRatio="none" role="img" '
        f'aria-label="{esc(series[0].name)}">'
        f'<g class="trend-grid">{grid}</g>'
        + "".join(blocks)
        + "</svg>"
        + "".join(dots)
        + "</div>"
        "</div>"
        f'<div class="trend-x">{x_labels}</div>'
        f"{legend}"
        "</div>"
    )
