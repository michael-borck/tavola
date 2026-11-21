"""Donut share: parts of a whole as a single SVG ring."""

from __future__ import annotations

from tavola.layouts._charts import build_chart, donut_figure, donut_legend
from tavola.layouts._parts import claim_list, rail_header, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    model = build_chart(ctx)
    if len(model.claims) < 2 or model.total <= 0:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )

    return (
        '<section class="donut-share">'
        + rail_header(model.kicker, model.title)
        + '<div class="donut-body">'
        + donut_figure(model)
        + donut_legend(model)
        + "</div>"
        + "</section>"
    )


register(
    Layout(
        id="donut-share",
        name="Donut share",
        description=(
            "Parts of one whole as a donut chart with a legend. Use only when "
            "the numbers share a unit and represent shares or parts."
        ),
        needs=("multi_numeric", "chartable"),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
