"""Shared HTML parts for layouts.

Every interpolation of model-provided text goes through ``esc``. Layouts should
compose these helpers rather than build HTML from raw strings.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from tavola.brief import Claim

if TYPE_CHECKING:
    from tavola.layouts.base import LayoutContext


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def stat_cards(
    claims: list[Claim], *, limit: int = 3
) -> tuple[str, list[Claim]]:
    """Render up to ``limit`` numeric claims; return the HTML and the rest."""
    numeric = [claim for claim in claims if claim.value][:limit]
    cards = "".join(
        '<div class="stat">'
        f'<span class="stat-value">{esc(claim.value)}</span>'
        f'<span class="stat-label">{esc(claim.label or claim.text)}</span>'
        "</div>"
        for claim in numeric
    )
    chosen = {id(claim) for claim in numeric}
    rest = [claim for claim in claims if id(claim) not in chosen]
    return f'<div class="stat-row">{cards}</div>', rest


def claim_list(
    claims: list[Claim],
    *,
    numbered: bool = False,
    limit: int = 6,
    compact: bool = False,
) -> str:
    """An unordered (or numbered) claim list with optional source pills."""
    classes = "claim-list compact" if compact else "claim-list"
    items: list[str] = []
    for index, claim in enumerate(claims[:limit], start=1):
        marker = (
            f'<span class="claim-marker">{index:02d}</span>' if numbered else ""
        )
        source = (
            f'<span class="claim-source">{esc(claim.source)}</span>'
            if claim.source
            else ""
        )
        items.append(
            '<li class="claim">'
            f"{marker}"
            f'<span class="claim-text">{esc(claim.text)}</span>'
            f"{source}"
            "</li>"
        )
    return f'<ul class="{classes}">{"".join(items)}</ul>'


def thesis(text: str, *, extra: str = "") -> str:
    return f'<p class="thesis {extra}">{esc(text)}</p>' if extra else (
        f'<p class="thesis">{esc(text)}</p>'
    )


def quote_block(quote: str) -> str:
    return f'<blockquote class="quote">“{esc(quote)}”</blockquote>'


def rail_header(kicker: str, title: str) -> str:
    return (
        '<div class="rail-head">'
        f'<span class="rail-kicker">{esc(kicker)}</span>'
        f'<h2 class="rail-title">{esc(title)}</h2>'
        "</div>"
    )


def eyebrow(text: str) -> str:
    return f'<p class="eyebrow">{esc(text)}</p>'


def proportion_claims(ctx: LayoutContext) -> list[Claim]:
    """Prefer the claims named by a proportion relationship over extra totals."""
    numeric = [claim for claim in ctx.numeric_claims() if claim.value]
    relationship = ctx.relationship("proportion")
    if relationship is None or not relationship.items:
        return numeric

    matched: list[Claim] = []
    used: set[int] = set()
    for item in relationship.items:
        name = item.casefold().strip()
        if not name:
            continue
        candidates: list[tuple[int, int, Claim]] = []
        for claim in numeric:
            if id(claim) in used:
                continue
            label = (claim.label or "").casefold()
            text = claim.text.casefold()
            if name == label or name == text:
                rank = 0
            elif label.startswith(name) or text.startswith(name):
                rank = 1
            elif name in label or name in text:
                rank = 2
            else:
                continue
            candidates.append((rank, len(label or text), claim))
        if candidates:
            candidates.sort(key=lambda candidate: (candidate[0], candidate[1]))
            claim = candidates[0][2]
            used.add(id(claim))
            matched.append(claim)

    return matched if len(matched) >= 2 else numeric
