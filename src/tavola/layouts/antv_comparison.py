"""AntV comparison: two sides with a central vs divider."""

from __future__ import annotations

from tavola.antv import render_antv, theme_block
from tavola.layouts._parts import claim_list, esc, rail_header, thesis
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
    claims = ctx.brief.claims
    midpoint = max(1, len(claims) // 2)
    left_claims = claims[:midpoint][:3]
    right_claims = claims[midpoint:][:3] or claims[:2]

    def children(items: list) -> str:
        return "\n".join(
            f"        - label {claim.label or claim.text}" for claim in items
        )

    syntax = (
        "infographic compare-binary-horizontal-simple-vs\n"
        f"{theme_block(ctx.theme)}\n"
        "data\n  items\n"
        f"    - label {left}\n"
        "      children\n"
        f"{children(left_claims)}\n"
        f"    - label {right}\n"
        "      children\n"
        f"{children(right_claims)}"
    )
    svg = render_antv(syntax, width=ctx.width, height=ctx.height, theme=ctx.theme)
    return (
        '<section class="antv-layout">'
        + rail_header("Compare", relationship.summary)
        + '<div class="antv-compare-head">'
        + f'<span>{esc(left)}</span><b>vs</b><span>{esc(right)}</span>'
        + "</div>"
        + f'<div class="antv-figure">{svg}</div>'
        + "</section>"
    )


register(
    Layout(
        id="antv-comparison",
        name="AntV comparison",
        description=(
            "Two sides with a central vs divider, rendered by AntV "
            "Infographic. Use when the source has a clear trade-off."
        ),
        needs=("comparison",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
        family="diagram",
    )
)
