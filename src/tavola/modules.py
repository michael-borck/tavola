"""Reusable composition modules.

Layouts own the page structure. Modules own the smaller, repeatable fragments
inside a composition: KPI tiles, insight rails, chart legends, and so on.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tavola.icons import icon_html, icon_svg
from tavola.layouts._parts import esc

if TYPE_CHECKING:
    from tavola.layouts.base import LayoutContext


@dataclass(frozen=True)
class Module:
    id: str
    name: str
    description: str
    needs: tuple[str, ...]
    render: Callable[[LayoutContext], str]


_MODULES: dict[str, Module] = {}


def register(module: Module) -> Module:
    if module.id in _MODULES:
        raise ValueError(f"Module id {module.id!r} is already registered.")
    _MODULES[module.id] = module
    return module


def get_module(module_id: str) -> Module:
    try:
        return _MODULES[module_id]
    except KeyError:
        known = ", ".join(sorted(_MODULES)) or "none"
        raise KeyError(f"Unknown module {module_id!r}; known: {known}.") from None


def catalog() -> list[Module]:
    return [_MODULES[key] for key in sorted(_MODULES)]


def risk_guard(ctx: LayoutContext) -> str:
    from tavola.brief import Risk

    risks = list(ctx.brief.risks[:2])
    if not risks:
        cause = ctx.relationship("cause")
        if cause is not None and len(cause.items) >= 2:
            risks = [
                Risk(risk=cause.items[0], mitigation=cause.items[1])
            ]
    rows = []
    for risk in risks:
        mitigation = (
            f'<p class="guard-mitigation"><strong>Mitigate:</strong> '
            f"{esc(risk.mitigation)}</p>"
            if risk.mitigation
            else ""
        )
        rows.append(
            '<div class="guard">'
            f'<span class="guard-icon">{icon_svg("shield-check")}</span>'
            "<div><h3>Risk</h3>"
            f"<p>{esc(risk.risk)}</p>{mitigation}</div>"
            "</div>"
        )
    return f'<aside class="guard-band">{"".join(rows)}</aside>' if rows else ""


def kpi_tiles(ctx: LayoutContext) -> str:
    claims = [claim for claim in ctx.brief.claims if claim.value][:3]
    if not claims:
        return ""
    tiles = "".join(
        '<div class="td-kpi">'
        '<div class="td-kpi-head">'
        f'{icon_html(claim.label, claim.text)}'
        f'<strong>{esc(claim.value)}</strong>'
        "</div>"
        f'<span>{esc(claim.label or claim.text)}</span>'
        "</div>"
        for claim in claims
    )
    return f'<div class="td-kpis">{tiles}</div>'


def evidence_table(ctx: LayoutContext) -> str:
    claims = [claim for claim in ctx.brief.claims if claim.source][:4]
    if len(claims) < 2:
        return ""
    rows = "".join(
        "<tr>"
        f"<td>{esc(claim.text)}</td>"
        f"<td>{esc(claim.value or '—')}</td>"
        f"<td>{esc(claim.source or '')}</td>"
        "</tr>"
        for claim in claims
    )
    return (
        '<table class="evidence-table">'
        "<thead><tr><th>Evidence</th><th>Figure</th><th>Source</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
    )


def insight_rail(ctx: LayoutContext) -> str:
    notes = [claim for claim in ctx.brief.claims if not claim.value][:2]
    note_html = "".join(
        '<li class="dash-note">'
        f'<span class="dash-note-index">{index:02d}</span>'
        f'<p>{esc(claim.text)}</p>'
        "</li>"
        for index, claim in enumerate(notes, start=1)
    )
    notes_list = f'<ul class="dash-notes">{note_html}</ul>' if note_html else ""
    return (
        '<aside class="dash-rail">'
        '<p class="rail-kicker">Read</p>'
        f'<p class="dash-thesis">{esc(ctx.brief.thesis)}</p>'
        f"{notes_list}"
        "</aside>"
    )


register(
    Module(
        id="kpi-tiles",
        name="KPI tiles",
        description="Up to three numeric claims as compact headline tiles.",
        needs=("multi_numeric",),
        render=kpi_tiles,
    )
)
register(
    Module(
        id="evidence-table",
        name="Evidence table",
        description="Cited claims as a compact evidence table.",
        needs=("sources",),
        render=evidence_table,
    )
)
register(
    Module(
        id="risk-guard",
        name="Risk guard",
        description="Up to two stated risks with their mitigations.",
        needs=("risks",),
        render=risk_guard,
    )
)
register(
    Module(
        id="insight-rail",
        name="Insight rail",
        description="The thesis and up to two qualitative claims in a side rail.",
        needs=(),
        render=insight_rail,
    )
)
