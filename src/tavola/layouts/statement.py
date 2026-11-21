"""Statement: a large quote or thesis with supporting evidence."""

from __future__ import annotations

from tavola.layouts._parts import claim_list, quote_block, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    lead = (
        quote_block(ctx.brief.quote)
        if ctx.brief.quote
        else thesis(ctx.brief.thesis, extra="statement-thesis")
    )
    return (
        '<section class="statement">'
        f"{lead}"
        '<div class="support">'
        f"{claim_list(ctx.brief.claims, numbered=True, limit=4)}"
        "</div>"
        "</section>"
    )


register(
    Layout(
        id="statement",
        name="Statement",
        description="A strong quote or argument with a few supporting points.",
        needs=("quote",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
