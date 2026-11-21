"""Shared illustrated hero band."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tavola.layouts.base import LayoutContext


def hero_art(ctx: LayoutContext) -> str:
    hero = ctx.assets.get("hero")
    if hero:
        encoded = base64.b64encode(hero).decode("ascii")
        return (
            '<div class="illus-art" aria-hidden="true">'
            f'<img src="data:image/png;base64,{encoded}" alt="">'
            "</div>"
        )
    seed = sum(ord(char) for char in ctx.brief.title) or 19
    shift = seed % 17
    rotation = seed % 47
    return (
        '<div class="illus-art" aria-hidden="true">'
        '<svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" role="presentation">'
        '<rect class="illus-bg" x="0" y="0" width="100" height="100" />'
        f'<circle class="illus-orb-a" cx="{68 + shift / 3:.1f}" cy="{30 + shift / 4:.1f}" r="22" />'
        f'<circle class="illus-orb-b" cx="{35 - shift / 4:.1f}" cy="{68 - shift / 5:.1f}" r="17" />'
        f'<path class="illus-ribbon" d="M 8 72 C 28 40, 58 96, 92 28" '
        f'transform="rotate({rotation} 50 50)" />'
        f'<path class="illus-line" d="M 12 18 L 88 18 M 12 28 L 62 28" />'
        '<circle class="illus-dot-a" cx="78" cy="72" r="2.2" />'
        '<circle class="illus-dot-b" cx="22" cy="32" r="1.4" />'
        "</svg>"
        "</div>"
    )
