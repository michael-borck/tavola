"""Bento: a mixed grid of claims, numbers, and a quote."""

from __future__ import annotations

from tavola.layouts._parts import esc
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    brief = ctx.brief
    cells: list[str] = [
        '<article class="bento-cell bento-wide bento-thesis">'
        f'<p class="bento-title">{esc(brief.thesis)}</p>'
        "</article>"
    ]

    numeric = ctx.numeric_claims()
    if numeric:
        hero = numeric[0]
        cells.append(
            '<article class="bento-cell bento-tall bento-figure">'
            f'<span class="stat-value">{esc(hero.value)}</span>'
            f'<span class="stat-label">{esc(hero.label or hero.text)}</span>'
            "</article>"
        )
    for claim in numeric[1:3]:
        cells.append(
            '<article class="bento-cell bento-stat">'
            f'<span class="stat-value">{esc(claim.value)}</span>'
            f'<span class="stat-label">{esc(claim.label or claim.text)}</span>'
            "</article>"
        )

    for claim in ctx.text_claims()[:2]:
        cells.append(
            '<article class="bento-cell bento-claim">'
            f'<p>{esc(claim.text)}</p>'
            + (
                f'<span class="claim-source">{esc(claim.source)}</span>'
                if claim.source
                else ""
            )
            + "</article>"
        )

    if brief.quote:
        cells.append(
            '<article class="bento-cell bento-quote">'
            f'<p>“{esc(brief.quote)}”</p>'
            "</article>"
        )

    return f'<section class="bento">{"".join(cells)}</section>'


register(
    Layout(
        id="bento",
        name="Bento",
        description="A mixed grid of five to seven claims, figures, and a quote.",
        needs=("many_claims",),
        min_claims=4,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
