"""Grouped bars: two series compared across the same labels."""

from __future__ import annotations

from tavola.layouts._parts import claim_list, esc, rail_header, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    series = ctx.brief.series
    if len(series) < 2:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )
    left, right = series[0], series[1]
    labels = left.labels[: min(len(left.labels), len(right.values), 8)]
    values = [
        (left.values[i], right.values[i])
        for i in range(len(labels))
    ]
    top = max(value for pair in values for value in pair) or 1.0
    groups = "".join(
        '<div class="gb-group">'
        '<div class="gb-bars">'
        f'<span class="gb-bar gb-bar-1" style="height: {a / top * 100:.1f}%"></span>'
        f'<span class="gb-bar gb-bar-2" style="height: {b / top * 100:.1f}%"></span>'
        "</div>"
        f'<span class="gb-label">{esc(label)}</span>'
        "</div>"
        for label, (a, b) in zip(labels, values, strict=False)
    )
    return (
        '<section class="grouped-bars">'
        + rail_header("Compare", f"{left.name} vs {right.name}")
        + f'<div class="gb-plot">{groups}</div>'
        + '<div class="gb-legend">'
        + f'<span><i class="gb-swatch-1"></i>{esc(left.name)}</span>'
        + f'<span><i class="gb-swatch-2"></i>{esc(right.name)}</span>'
        + "</div>"
        + "</section>"
    )


register(
    Layout(
        id="grouped-bars",
        name="Grouped bars",
        description=(
            "Two aligned series compared across the same labels. Use when the "
            "source has two measures over the same categories."
        ),
        needs=("series", "multi_series"),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
