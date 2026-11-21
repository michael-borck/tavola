"""Trend: one small ordered series as an SVG line chart."""

from __future__ import annotations

from tavola.layouts._charts import trend_figure, trend_range
from tavola.layouts._parts import claim_list, esc, rail_header, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    if not ctx.brief.series:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )
    series = ctx.brief.series
    unit = series[0].unit or ""
    low, high = trend_range(series)
    title = series[0].name if len(series) == 1 else " + ".join(s.name for s in series)
    return (
        '<section class="trend">'
        + rail_header("Trend", title)
        + trend_figure(series)
        + '<p class="trend-note">'
        + f"{esc(series[0].labels[0])}–{esc(series[0].labels[-1])}"
        + (f" · {esc(unit)}" if unit else "")
        + f" · low {low:g} · high {high:g}"
        + "</p>"
        + "</section>"
    )


register(
    Layout(
        id="trend",
        name="Trend",
        description=(
            "One or two ordered series as a line chart. Use only when the source "
            "contains actual time-ordered values."
        ),
        needs=("series",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
