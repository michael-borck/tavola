"""Illustrated quote: a generated hero visual around a strong line."""

from __future__ import annotations

from tavola.layouts._illustration import hero_art
from tavola.layouts._parts import claim_list, esc
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    quote = ctx.brief.quote or ctx.brief.thesis
    support = ctx.brief.thesis if ctx.brief.quote else ctx.brief.dek
    notes = [claim for claim in ctx.brief.claims if not claim.value][:2]
    note_html = "".join(
        f'<li class="iq-note"><p>{esc(claim.text)}</p></li>' for claim in notes
    )
    lower = (
        f'<ul class="iq-notes">{note_html}</ul>'
        if note_html
        else claim_list(ctx.brief.claims, limit=3)
    )
    return (
        '<section class="illustrated-quote">'
        '<div class="illus-hero it-hero">'
        + hero_art(ctx)
        + '<div class="illus-overlay iq-overlay">'
        '<p class="rail-kicker">In one line</p>'
        f'<blockquote class="iq-quote">“{esc(quote)}”</blockquote>'
        f'<p class="illus-dek">{esc(support)}</p>'
        "</div>"
        "</div>"
        f'<div class="iq-lower">{lower}</div>'
        "</section>"
    )


register(
    Layout(
        id="illustrated-quote",
        name="Illustrated quote",
        description=(
            "A generated hero visual carrying a large quote or thesis, with a "
            "short supporting band."
        ),
        needs=(),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
        family="illustrated",
    )
)
