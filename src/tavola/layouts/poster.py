"""Poster: a large quote or thesis beside abstract data-inspired geometry."""

from __future__ import annotations

from tavola.layouts._parts import esc
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    brief = ctx.brief
    lead = brief.quote or brief.thesis
    sub = brief.thesis if brief.quote else brief.dek
    seed = sum(ord(char) for char in brief.title) or 17
    angle = seed % 360
    shift = seed % 14
    claim_html = "".join(
        '<li class="poster-claim">'
        f'<span>{esc(claim.value or claim.label or claim.text)}</span>'
        f"<p>{esc(claim.text)}</p>"
        "</li>"
        for claim in brief.claims[:2]
    )
    art = (
        '<svg class="poster-svg" viewBox="0 0 100 100" role="img" '
        f'aria-label="{esc(brief.title)}">'
        f'<circle class="poster-ring poster-ring-1" cx="{50 + shift}" cy="46" r="36" />'
        f'<circle class="poster-ring poster-ring-2" cx="{44 - shift / 2:.1f}" cy="54" r="27" />'
        f'<path class="poster-arc" d="M 18 62 A 34 34 0 0 1 74 28" />'
        f'<circle class="poster-dot poster-dot-1" cx="{72 + shift / 3:.1f}" cy="24" r="4.2" />'
        f'<circle class="poster-dot poster-dot-2" cx="{24 - shift / 3:.1f}" cy="70" r="2.6" />'
        '<path class="poster-slash" d="M 12 82 L 88 18" />'
        "</svg>"
    )
    return (
        '<section class="poster-layout">'
        '<div class="poster-copy">'
        '<p class="rail-kicker">Field note</p>'
        f'<blockquote class="poster-quote">“{esc(lead)}”</blockquote>'
        f'<p class="poster-sub">{esc(sub)}</p>'
        f'<ul class="poster-claims">{claim_html}</ul>'
        "</div>"
        f'<div class="poster-art" style="--poster-angle: {angle}deg">{art}</div>'
        "</section>"
    )


register(
    Layout(
        id="poster",
        name="Poster",
        description=(
            "A large quote or thesis with supporting points and abstract "
            "geometry. Use for a strong argument or a memorable line."
        ),
        needs=(),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
