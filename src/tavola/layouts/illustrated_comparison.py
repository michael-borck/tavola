"""Illustrated comparison: hero art with two evidence sides."""

from __future__ import annotations

from tavola.layouts._illustration import hero_art
from tavola.layouts._parts import claim_list, esc, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    relationship = ctx.relationship("comparison")
    if relationship is None or len(relationship.items) < 2:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )
    left, right = relationship.items[:2]
    midpoint = max(1, len(ctx.brief.claims) // 2)
    left_claims = ctx.brief.claims[:midpoint][:3]
    right_claims = ctx.brief.claims[midpoint:][:3] or ctx.brief.claims[:2]
    return (
        '<section class="illustrated-comparison">'
        '<div class="illus-hero it-hero">'
        + hero_art(ctx)
        + '<div class="illus-overlay">'
        '<p class="rail-kicker">The trade-off</p>'
        f'<p class="illus-lead">{esc(ctx.brief.thesis)}</p>'
        "</div>"
        "</div>"
        '<div class="illus-compare">'
        '<div class="ic-side">'
        f'<h3>{esc(left)}</h3>'
        f"{claim_list(left_claims, limit=3)}"
        "</div>"
        '<span class="ic-vs">vs</span>'
        '<div class="ic-side">'
        f'<h3>{esc(right)}</h3>'
        f"{claim_list(right_claims, limit=3)}"
        "</div>"
        "</div>"
        "</section>"
    )


register(
    Layout(
        id="illustrated-comparison",
        name="Illustrated comparison",
        description=(
            "A generated hero visual with two evidence sides and a central vs "
            "divider. Use for a clear trade-off."
        ),
        needs=("comparison",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
        family="illustrated",
    )
)
