"""Comparison: two sides with evidence and a verdict."""

from __future__ import annotations

from tavola.layouts._parts import claim_list, esc
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    left_title, right_title = ctx.comparison_items()
    claims = ctx.brief.claims
    midpoint = max(1, len(claims) // 2)
    left_claims = claims[:midpoint][:3]
    right_claims = claims[midpoint:][:3]
    if not right_claims:
        right_claims = claims[:2]

    return (
        '<section class="compare">'
        '<div class="compare-side">'
        f'<h3 class="compare-title">{esc(left_title)}</h3>'
        f"{claim_list(left_claims, limit=3)}"
        "</div>"
        '<span class="compare-vs">vs</span>'
        '<div class="compare-side compare-side-right">'
        f'<h3 class="compare-title">{esc(right_title)}</h3>'
        f"{claim_list(right_claims, limit=3)}"
        "</div>"
        "</section>"
        f'<p class="compare-verdict">{esc(ctx.brief.thesis)}</p>'
    )


register(
    Layout(
        id="comparison",
        name="Comparison",
        description="Two sides, a trade-off, or a before-and-after with evidence.",
        needs=("comparison",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
