"""Vision scoring for best-of-N pages."""

from __future__ import annotations

from typing import Any

from tavola.brief import Brief
from tavola.design import DesignPlan
from tavola.judge import VisualScore, score_page


class ImageLLM:
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.images: list[bytes] = []
        self.messages: list[list[dict[str, Any]]] = []

    def json(self, messages, *, schema, **kwargs):  # type: ignore[no-untyped-def]
        self.messages.append(messages)
        self.images = kwargs["images"]
        return {
            "legibility": 8,
            "composition": 7,
            "hierarchy": 9,
            "reason": "Clear title and a readable number.",
        }


def test_visual_score_weights_legibility() -> None:
    score = VisualScore(legibility=10, composition=5, hierarchy=5)
    assert score.total == 70.0


def test_score_page_sends_the_render_and_brief(brief: Brief, plan: DesignPlan) -> None:
    llm = ImageLLM()
    score = score_page(brief, plan, b"png-bytes", llm)  # type: ignore[arg-type]

    assert score.total == 80.0
    assert llm.images == [b"png-bytes"]
    assert "TITLE:" in llm.messages[-1][-1]["content"]
    assert brief.title in llm.messages[-1][-1]["content"]
