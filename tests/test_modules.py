"""Composition module registry."""

from __future__ import annotations

from tavola.brief import Brief
from tavola.config import ORIENTATIONS
from tavola.design import DesignPlan
from tavola.layouts import LayoutContext, get_layout
from tavola.modules import catalog, get_module
from tavola.themes import get_theme


def _context(brief: Brief) -> LayoutContext:
    plan = DesignPlan(
        layout="dashboard",
        style="professional",
        orientation="portrait",
        density="standard",
    )
    return LayoutContext(
        brief=brief,
        plan=plan,
        theme=get_theme("professional"),
        size=ORIENTATIONS["portrait"],
    )


def test_module_catalog() -> None:
    ids = {module.id for module in catalog()}
    assert ids == {
        "evidence-table",
        "insight-rail",
        "kpi-tiles",
        "risk-guard",
    }
    assert get_module("kpi-tiles").needs == ("multi_numeric",)


def test_modules_render(brief: Brief) -> None:
    ctx = _context(brief)
    kpis = get_module("kpi-tiles").render(ctx)
    rail = get_module("insight-rail").render(ctx)
    assert kpis.count('class="td-kpi"') == 3
    assert 'class="dash-rail"' in rail
    assert brief.thesis in rail
    assert get_layout("dashboard").id == "dashboard"


def test_evidence_table_renders_cited_claims(brief: Brief) -> None:
    ctx = _context(brief)
    html = get_module("evidence-table").render(ctx)
    assert 'class="evidence-table"' in html
    assert "p. 12" in html
    assert "<th>Evidence</th>" in html


def test_risk_guard_renders_pairs() -> None:
    from tavola.brief import Claim, Risk

    brief = Brief(
        title="T",
        dek="D",
        thesis="H",
        claims=[Claim(text="A"), Claim(text="B"), Claim(text="C")],
        risks=[
            Risk(risk="Dry spring", mitigation="Backup watering crew"),
            Risk(risk="Cost overrun", mitigation="12% contingency"),
        ],
        bottom_line="B",
    )
    html = get_module("risk-guard").render(_context(brief))
    assert 'class="guard-band"' in html
    assert "Backup watering crew" in html
    assert "12% contingency" in html
