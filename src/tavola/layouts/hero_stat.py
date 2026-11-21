"""Hero stat: one headline number with context."""

from __future__ import annotations

from tavola.layouts._parts import claim_list, esc, stat_cards, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    hero = ctx.hero_claim()
    if hero is None:
        return (
            '<section class="hero hero-text">'
            '<div class="hero-copy">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
            "</section>"
        )

    others = [claim for claim in ctx.numeric_claims() if id(claim) != id(hero)]
    support_html, _ = stat_cards(others, limit=2)
    support = support_html if others else ""

    text_claims = [
        claim for claim in ctx.brief.claims if id(claim) != id(hero) and not claim.value
    ]
    bullets = claim_list(text_claims, limit=3, compact=True) if text_claims else ""

    return (
        '<section class="hero">'
        '<div class="hero-figure">'
        f'<span class="hero-value">{esc(hero.value)}</span>'
        f'<span class="hero-label">{esc(hero.label or hero.text)}</span>'
        "</div>"
        '<div class="hero-copy">'
        f"{thesis(ctx.brief.thesis)}"
        f"{bullets}"
        "</div>"
        "</section>"
        f"{support}"
    )


register(
    Layout(
        id="hero-stat",
        name="Hero stat",
        description="One headline number with supporting context and a short list.",
        needs=("numeric",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
