"""Dashboard: one dominant chart with a short insight rail."""

from __future__ import annotations

from tavola.layouts._charts import (
    bar_rows,
    build_chart,
    donut_figure,
    donut_legend,
)
from tavola.layouts._parts import claim_list, rail_header, thesis
from tavola.layouts.base import Layout, LayoutContext, register
from tavola.modules import get_module


def render(ctx: LayoutContext) -> str:
    model = build_chart(ctx)
    if len(model.claims) < 2 or model.total <= 0:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )

    if model.share_mode:
        visual = (
            '<div class="dash-donut">'
            + donut_figure(model)
            + donut_legend(model)
            + "</div>"
        )
    else:
        visual = (
            f'<ul class="dash-bars">{bar_rows(model)}</ul>'
            f'<p class="bar-note">{model.note}</p>'
        )

    return (
        '<section class="dashboard">'
        '<div class="dash-main">'
        + rail_header("Dashboard", model.title)
        + visual
        + "</div>"
        + get_module("insight-rail").render(ctx)
        + "</section>"
    )


register(
    Layout(
        id="dashboard",
        name="Dashboard",
        description=(
            "A dominant chart beside a short insight rail. Best when the Brief "
            "has several numbers and at least one qualitative claim."
        ),
        needs=("multi_numeric", "chartable"),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
