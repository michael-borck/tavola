"""Trend dashboard: KPI tiles, a line chart, and an insight rail."""

from __future__ import annotations

from tavola.layouts._charts import trend_figure
from tavola.layouts._parts import claim_list, rail_header, thesis
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
    kpi_row = get_module("kpi-tiles").render(ctx)
    return (
        '<section class="trend-dashboard">'
        '<div class="td-main">'
        + rail_header(
            "Trend",
            series[0].name if len(series) == 1 else " + ".join(s.name for s in series),
        )
        + kpi_row
        + trend_figure(series)
        + "</div>"
        + '<aside class="dash-rail">'
        + '<p class="rail-kicker">Read</p>'
        + get_module("insight-rail").render(ctx)
        + "</section>"
    )


register(
    Layout(
        id="trend-dashboard",
        name="Trend dashboard",
        description=(
            "KPI tiles and a line chart beside a short insight rail. Best when "
            "the source has ordered series plus headline values."
        ),
        needs=("series",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
