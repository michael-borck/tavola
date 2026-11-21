"""Quadrant: four claims arranged as competing priorities."""

from __future__ import annotations

from tavola.icons import icon_html
from tavola.layouts._parts import claim_list, esc, rail_header, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    claims = ctx.brief.claims[:4]
    if len(claims) < 4:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )
    cells = "".join(
        '<article class="q-cell">'
        f"{icon_html(claim.label, claim.text)}"
        f'<h3>{esc(claim.label or claim.text)}</h3>'
        f"<p>{esc(claim.text)}</p>"
        "</article>"
        for claim in claims
    )
    return (
        '<section class="quadrant">'
        + rail_header("Trade-offs", "Four priorities")
        + f'<div class="q-grid">{cells}</div>'
        + "</section>"
    )


register(
    Layout(
        id="quadrant",
        name="Quadrant",
        description=(
            "Four claims arranged in a two-by-two field. Use when the source "
            "offers four competing priorities or trade-offs."
        ),
        needs=(),
        min_claims=4,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
