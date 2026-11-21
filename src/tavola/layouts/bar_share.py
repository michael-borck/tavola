"""Bar share: comparable numbers as horizontal bars."""

from __future__ import annotations

from tavola.layouts._charts import bar_rows, build_chart
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
        '<section class="bar-share">'
        + rail_header(model.kicker, model.title)
        + f'<ul class="bar-list">{bar_rows(model)}</ul>'
        + f'<p class="bar-note">{model.note}</p>'
        + "</section>"
    )


register(
    Layout(
        id="bar-share",
        name="Bar share",
        description=(
            "Three or four comparable numbers as horizontal bars; use when the "
            "numbers are parts of one whole or share a unit."
        ),
        needs=("multi_numeric", "chartable"),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
