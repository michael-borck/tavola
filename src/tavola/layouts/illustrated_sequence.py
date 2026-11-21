"""Illustrated sequence: hero art, KPI tiles, and a native flow band."""

from __future__ import annotations

from tavola.icons import icon_html
from tavola.layouts._illustration import hero_art
from tavola.layouts._parts import claim_list, esc, thesis
from tavola.layouts.base import Layout, LayoutContext, register
from tavola.modules import get_module


def render(ctx: LayoutContext) -> str:
    relationship = ctx.relationship("sequence")
    if relationship is None or len(relationship.items) < 2:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )
    steps = relationship.items[:5]
    step_html = "".join(
        '<li class="it-step">'
        '<div class="it-step-head">'
        f'<span class="it-step-num">{index:02d}</span>'
        f"{icon_html(step)}"
        "</div>"
        f'<p>{esc(step)}</p>'
        "</li>"
        for index, step in enumerate(steps, start=1)
    )
    guards = get_module("risk-guard").render(ctx)
    return (
        '<section class="illustrated-sequence">'
        '<div class="illus-hero it-hero">'
        + hero_art(ctx)
        + '<div class="illus-overlay">'
        '<p class="rail-kicker">The idea</p>'
        f'<p class="illus-lead">{esc(ctx.brief.thesis)}</p>'
        "</div>"
        "</div>"
        '<div class="it-lower">'
        + get_module("kpi-tiles").render(ctx)
        + '<div class="it-track">'
        '<svg class="it-track-svg" viewBox="0 0 100 20" '
        'preserveAspectRatio="none" aria-hidden="true">'
        '<path d="M 0 13 C 18 2, 32 18, 50 10 S 82 2, 100 12" /></svg>'
        + f'<ol class="it-flow">{step_html}</ol>'
        + "</div>"
        + guards
        + "</div>"
        + "</section>"
    )


register(
    Layout(
        id="illustrated-sequence",
        name="Illustrated sequence",
        description=(
            "A generated hero visual, KPI tiles, and a horizontal sequence of "
            "steps. Use when the source describes an ordered process."
        ),
        needs=("sequence",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
        family="illustrated",
    )
)
