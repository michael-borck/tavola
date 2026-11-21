"""Process: numbered steps, horizontal in landscape and vertical in portrait."""

from __future__ import annotations

from tavola.icons import icon_html
from tavola.layouts._parts import esc, rail_header
from tavola.layouts.base import Layout, LayoutContext, register
from tavola.modules import get_module


def render(ctx: LayoutContext) -> str:
    items = ctx.sequence_items()
    relationship = ctx.relationship("sequence")
    summary = relationship.summary if relationship else "How it works"

    steps: list[str] = []
    for index, label in enumerate(items[:5], start=1):
        steps.append(
            '<article class="step">'
            f'<span class="step-number">{index:02d}</span>'
            f'<h3 class="step-label">{esc(label)}</h3>'
            "</article>"
        )

    notes = [claim for claim in ctx.brief.claims if not claim.value][:2]
    note_html = "".join(
        '<li class="process-note">'
        f'{icon_html(claim.label, claim.text)}'
        f'<p>{esc(claim.text)}</p>'
        "</li>"
        for claim in notes
    )
    note_band = (
        f'<ul class="process-notes">{note_html}</ul>' if note_html else ""
    )
    guards = get_module("risk-guard").render(ctx)
    return (
        '<div class="layout-group process-layout">'
        + rail_header("Steps", summary)
        + f'<p class="process-thesis">{esc(ctx.brief.thesis)}</p>'
        + f'<section class="steps">{"".join(steps)}</section>'
        + note_band
        + guards
        + "</div>"
    )


register(
    Layout(
        id="process",
        name="Process",
        description="Numbered steps that explain how something works or is done.",
        needs=("sequence",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
