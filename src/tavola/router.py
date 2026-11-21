"""Optional System One router: choose one valid layout with Tev."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import requests

from tavola.brief import Brief
from tavola.compose import Composition


class RouterError(Exception):
    """Raised when a decision model cannot return a usable choice."""


@dataclass(frozen=True)
class RouteDecision:
    layout: str
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)

    @property
    def probability(self) -> float:
        return self.probabilities.get(self.layout, self.confidence)


_INSTRUCTIONS = """\
Choose the one-page composition that will make this Brief clearest.
The candidates are already valid. Prefer a chart only when the numbers share a
unit or make up a whole; prefer an editorial or statement layout when the
evidence is mostly qualitative. Do not choose a layout that would hide a key
number.
"""


def route_layout(
    brief: Brief,
    *,
    base_url: str,
    model: str,
    candidates: list[Composition],
    timeout: float = 60.0,
) -> RouteDecision:
    """Ask a decision model to pick one of the ranked candidates."""
    if len(candidates) < 2:
        raise RouterError("Routing needs at least two candidate layouts.")
    criteria = {
        item.layout: f"{_description(item.layout)}. Why it fits: {item.reason}."
        for item in candidates
    }
    state = {
        "title": brief.title,
        "dek": brief.dek,
        "thesis": brief.thesis,
        "claims": [
            claim.model_dump(exclude_none=True) for claim in brief.claims
        ],
        "relationships": [
            relationship.model_dump(exclude_none=True)
            for relationship in brief.relationships
        ],
        "quote": brief.quote,
    }
    payload = {
        "model": model,
        "state": state,
        "questions": {
            "layout": {
                "type": "choice",
                "instructions": _INSTRUCTIONS,
                "criteria": criteria,
            }
        },
    }
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/v1/systemone",
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise RouterError(f"Could not reach the router at {base_url}: {e}") from e
    if response.status_code >= 400:
        raise RouterError(
            f"Router returned {response.status_code}: "
            f"{response.text.strip() or response.reason}"
        )
    data = response.json()
    answers = data.get("answers") if isinstance(data, dict) else None
    answer = answers.get("layout") if isinstance(answers, dict) else None
    if not isinstance(answer, dict):
        raise RouterError("The router returned no layout answer.")
    choice = str(answer.get("choice") or "")
    if choice not in criteria:
        raise RouterError(f"The router chose an unknown layout {choice!r}.")
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict):
        probabilities = {}
    usage = data.get("usage") if isinstance(data, dict) else None
    return RouteDecision(
        layout=choice,
        confidence=float(answer.get("confidence") or 0.0),
        probabilities={
            str(key): float(value) for key, value in probabilities.items()
        },
        usage=usage if isinstance(usage, dict) else {},
    )


def _description(layout_id: str) -> str:
    from tavola.layouts import get_layout

    return get_layout(layout_id).description
