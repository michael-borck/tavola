"""Vision scoring for best-of-N candidate pages.

A candidate is a rendered PNG. The judge sees only the image plus the brief's
title and key claims, so it cannot reward a plan it has not actually seen.
Text-only models fail here; callers treat that as a signal to keep the first
candidate that passed the measured gate.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from tavola.brief import Brief
from tavola.design import DesignPlan
from tavola.llm import LLMProvider


class VisualScore(BaseModel):
    """One judge's view of a rendered page, each axis 0-10."""

    legibility: float = Field(ge=0, le=10)
    composition: float = Field(ge=0, le=10)
    hierarchy: float = Field(ge=0, le=10)
    reason: str = ""

    @property
    def total(self) -> float:
        """Weighted 0-100 score; legibility matters most."""
        return round(
            (self.legibility * 0.4 + self.composition * 0.3 + self.hierarchy * 0.3)
            * 10,
            1,
        )


_SYSTEM = """\
You are a strict art director reviewing one rendered infographic page.
Score only what you can see. Do not reward decoration or penalise a plain page
that is exceptionally clear.

- legibility: is every word readable at a glance, including small labels?
- composition: are balance, spacing, alignment, and margins controlled?
  A large unused region is a composition problem; do not reward a page whose
  main content floats in the middle.
- hierarchy: does the eye move from title to thesis to evidence in order?

Return JSON with legibility, composition, hierarchy (each 0-10, where 7 is
competent and 10 is exceptional) and a one-sentence reason. JSON only.
"""


def score_page(
    brief: Brief,
    plan: DesignPlan,
    image: bytes,
    llm: LLMProvider,
) -> VisualScore:
    """Ask a vision model to score one rendered candidate."""
    claims = "\n".join(f"- {claim.text}" for claim in brief.claims[:8])
    prompt = (
        f"TITLE: {brief.title}\n"
        f"DEK: {brief.dek}\n"
        f"THESIS: {brief.thesis}\n"
        f"CLAIMS:\n{claims}\n\n"
        f"PLAN: {plan.layout} · {plan.style} · {plan.density}\n\n"
        "Score this page."
    )
    raw = llm.json(
        [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        schema=VisualScore,
        images=[image],
        temperature=0.1,
        max_tokens=500,
    )
    return VisualScore.model_validate(raw)
