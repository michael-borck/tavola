"""Illustrated brief: a hero visual, thesis, stat strip, and support notes."""

from __future__ import annotations

from tavola.icons import icon_html
from tavola.layouts._illustration import hero_art
from tavola.layouts._parts import claim_list, esc
from tavola.layouts.base import Layout, LayoutContext, register
from tavola.modules import get_module


def _art(ctx: LayoutContext) -> str:
    return hero_art(ctx)

def render(ctx: LayoutContext) -> str:
    evidence = get_module("evidence-table").render(ctx)
    notes = [claim for claim in ctx.brief.claims if not claim.value][:2]
    note_html = "".join(
        '<li class="illus-note">'
        f'<span class="illus-note-icon">{icon_html(claim.label, claim.text)}</span>'
        f'<p>{esc(claim.text)}</p>'
        "</li>"
        for claim in notes
    )
    lower_notes = evidence or (
        f'<ul class="illus-notes">{note_html}</ul>' if note_html else ""
    )
    kpis = get_module("kpi-tiles").render(ctx)
    if not kpis and not lower_notes:
        lower_notes = claim_list(ctx.brief.claims, limit=3)
        kpis = ""

    sequence = ctx.relationship("sequence")
    flow = ""
    if sequence is not None and len(sequence.items) >= 2:
        steps = sequence.items[:5]
        flow = '<ol class="illus-flow">' + "".join(
            '<li class="illus-step">'
            f'<span class="illus-step-num">{index:02d}</span>'
            f"{icon_html(step)}"
            f'<p>{esc(step)}</p>'
            "</li>"
            for index, step in enumerate(steps, start=1)
        ) + "</ol>"
    guards = get_module("risk-guard").render(ctx)

    return (
        '<section class="illustrated">'
        '<div class="illus-hero">'
        + _art(ctx)
        + '<div class="illus-overlay">'
        '<p class="rail-kicker">The idea</p>'
        f'<p class="illus-lead">{esc(ctx.brief.thesis)}</p>'
        f'<p class="illus-dek">{esc(ctx.brief.dek)}</p>'
        "</div>"
        "</div>"
        '<div class="illus-lower">'
        f"{kpis}{lower_notes}{flow}{guards}"
        "</div>"
        "</section>"
    )


register(
    Layout(
        id="illustrated",
        name="Illustrated brief",
        description=(
            "A large conceptual visual with a thesis, KPI strip, and short "
            "supporting notes. Use for narrative explainers with a few numbers."
        ),
        needs=(),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
        family="illustrated",
    )
)
