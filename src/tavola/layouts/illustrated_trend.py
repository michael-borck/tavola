"""Illustrated trend: hero art, KPI tiles, and an ordered series."""

from __future__ import annotations

from tavola.layouts._charts import trend_figure
from tavola.layouts._illustration import hero_art
from tavola.layouts._parts import claim_list, esc, rail_header, thesis
from tavola.layouts.base import Layout, LayoutContext, register
from tavola.modules import get_module


def render(ctx: LayoutContext) -> str:
    if not ctx.brief.series:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )
    series = ctx.brief.series
    title = series[0].name if len(series) == 1 else " + ".join(s.name for s in series)
    return (
        '<section class="illustrated-trend">'
        '<div class="illus-hero it-hero">'
        + hero_art(ctx)
        + '<div class="illus-overlay">'
        '<p class="rail-kicker">The idea</p>'
        f'<p class="illus-lead">{esc(ctx.brief.thesis)}</p>'
        "</div>"
        "</div>"
        '<div class="it-lower">'
        + get_module("kpi-tiles").render(ctx)
        + '<div class="it-chart">'
        + rail_header("Trend", title)
        + trend_figure(series)
        + "</div>"
        + "</div>"
        + "</section>"
    )


register(
    Layout(
        id="illustrated-trend",
        name="Illustrated trend",
        description=(
            "A generated hero visual, KPI tiles, and a line chart. Use when the "
            "source has an ordered series plus headline values."
        ),
        needs=("series",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
        family="illustrated",
    )
)
