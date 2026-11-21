"""Stat row: three or four comparable figures with supporting claims."""

from __future__ import annotations

from tavola.layouts._parts import claim_list, stat_cards, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    cards, rest = stat_cards(ctx.brief.claims, limit=4)
    support = claim_list(rest, limit=4) if rest else ""
    return (
        '<div class="layout-group stat-layout">'
        f"{thesis(ctx.brief.thesis)}"
        f"{cards}"
        f"{support}"
        "</div>"
    )


register(
    Layout(
        id="stat-row",
        name="Stat row",
        description="Three or four comparable figures with supporting claims.",
        needs=("multi_numeric",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
