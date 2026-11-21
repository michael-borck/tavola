"""Deterministic composition features and candidate ranking.

Rules own the hard constraints; a model may later choose among the survivors.
This module never calls an LLM and never writes markup.
"""

from __future__ import annotations

from dataclasses import dataclass

from tavola.brief import Brief
from tavola.layouts import catalog, get_layout


@dataclass(frozen=True)
class Composition:
    layout: str
    score: int
    reason: str


def _looks_temporal(items: list[str]) -> bool:
    import re

    if not items:
        return False
    pattern = re.compile(
        r"\b(1[89]\d{2}|20\d{2}|Q[1-4]|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|"
        r"Nov|Dec|\d{1,2}:\d{2}|day|week|month|year|first|then|finally)\b",
        re.IGNORECASE,
    )
    return sum(1 for item in items if pattern.search(item)) >= max(1, len(items) // 2)


def is_chartable(brief: Brief) -> bool:
    """True when numeric claims can share one chart scale."""
    numeric = [claim for claim in brief.numeric_claims() if claim.numeric is not None]
    if len(numeric) < 3:
        return False
    if brief.relationship("proportion") is not None:
        return True
    units = {claim.unit for claim in numeric}
    return len(units) == 1


def _valid(layout_id: str, brief: Brief, orientation: str) -> bool:
    layout = get_layout(layout_id)
    if orientation not in layout.orientations:
        return False
    if not (layout.min_claims <= len(brief.claims) <= layout.max_claims):
        return False
    numeric = brief.numeric_claims()
    if "numeric" in layout.needs and not numeric:
        return False
    if "multi_numeric" in layout.needs and len(numeric) < 3:
        return False
    if "chartable" in layout.needs and not is_chartable(brief):
        return False
    if "series" in layout.needs and not brief.series:
        return False
    if "multi_series" in layout.needs and len(brief.series) < 2:
        return False
    if "comparison" in layout.needs:
        relationship = brief.relationship("comparison")
        if relationship is None or len(relationship.items) != 2:
            return False
    if "hierarchy" in layout.needs:
        relationship = brief.relationship("hierarchy")
        if relationship is None or len(relationship.items) < 3:
            return False
    return True


def rank_compositions(
    brief: Brief,
    *,
    orientation: str = "portrait",
    mode: str = "auto",
) -> list[Composition]:
    """Rank valid layouts from the Brief's actual data shape."""
    numeric = brief.numeric_claims()
    claim_count = len(brief.claims)
    comparison = brief.relationship("comparison")
    sequence = brief.relationship("sequence")
    proportion = brief.relationship("proportion")
    chartable = is_chartable(brief)
    percent_total = sum(
        abs(claim.numeric or 0.0)
        for claim in numeric
        if claim.unit == "%"
    )
    scores: dict[str, int] = {}
    reasons: dict[str, str] = {}

    def add(layout_id: str, score: int, reason: str) -> None:
        scores[layout_id] = scores.get(layout_id, 0) + score
        reasons.setdefault(layout_id, reason)

    if comparison is not None and len(comparison.items) == 2:
        add("comparison", 20, "two-sided relationship")
        add("antv-comparison", 12, "two-sided relationship")
        add("illustrated-comparison", 10, "two-sided relationship")
    hierarchy = brief.relationship("hierarchy")
    if hierarchy is not None and len(hierarchy.items) >= 3:
        add("hierarchy", 20, "root-and-branches relationship")
        add("antv-hierarchy", 12, "root-and-branches relationship")
    if sequence is not None and len(sequence.items) >= 2:
        if _looks_temporal(sequence.items):
            add("timeline", 20, "ordered dates or milestones")
        else:
            add("process", 20, "ordered steps")
        add("antv-sequence", 12, "ordered sequence")
        add("illustrated-sequence", 9, "ordered sequence")
    if brief.series:
        add("trend", 20, "ordered series")
        if len(brief.series) >= 2:
            add("grouped-bars", 18, "two series over shared labels")
        if numeric:
            add("trend-dashboard", 16, "series plus headline values")
            add("illustrated-trend", 16, "series plus an illustrated hero")
    if chartable and proportion is not None and len(numeric) >= 3:
        add("donut-share", 18, "part-to-whole relationship")
        add("bar-share", 14, "part-to-whole relationship")
        add("stacked-share", 10, "part-to-whole relationship")

    text_count = len([claim for claim in brief.claims if not claim.value])
    if chartable and len(numeric) >= 3 and text_count >= 1:
        add("dashboard", 9, "figures plus qualitative insight")
    if len(numeric) >= 3:
        add("stat-row", 10, "three or more figures")
        add("bento", 6, "mixed evidence")
        add("hero-stat", 4, "one headline figure")
        if chartable:
            add("bar-share", 8, "comparable figures")
        if chartable and (proportion is not None or 90 <= percent_total <= 110):
            add("donut-share", 6, "proportional figures")
    elif numeric:
        add("hero-stat", 10, "a headline figure")
        add("statement", 4, "argument-led page")
    else:
        add("statement", 8, "argument-led page")

    if brief.quote:
        add("statement", 4, "source quote")
        add("poster", 6, "source quote")
        add("illustrated-quote", 24, "source quote")
    if len(numeric) >= 2 and text_count >= 1:
        illustrated_score = 24 if any(claim.source for claim in brief.claims) else 21
        add("illustrated", illustrated_score, "visual explainer with mixed evidence")
    if claim_count >= 4:
        add("bento", 3, "enough evidence for a grid")
        add("quadrant", 4, "four competing priorities")
    if claim_count < 4:
        add("statement", 2, "short brief")

    ranked = [
        Composition(layout=layout.id, score=scores[layout.id], reason=reasons[layout.id])
        for layout in catalog()
        if layout.id in scores
        and _valid(layout.id, brief, orientation)
        and _family_allowed(layout.family, mode)
    ]
    ranked.sort(key=lambda item: (-item.score, item.layout))
    return ranked


def _family_allowed(family: str, mode: str) -> bool:
    if family == "diagram":
        return False
    if mode == "structured":
        return family != "illustrated"
    if mode == "illustrated":
        return family == "illustrated"
    return True


def valid_layout_ids(
    brief: Brief,
    *,
    orientation: str = "portrait",
    mode: str = "auto",
) -> list[str]:
    return [
        item.layout
        for item in rank_compositions(brief, orientation=orientation, mode=mode)
    ]
