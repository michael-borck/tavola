"""The pipeline with a fake provider, plus saving and the sidecar."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import tavola.core as core
from tavola.brief import Brief
from tavola.config import DEFAULT_CONFIG
from tavola.core import GenerateError, GenerateResult, default_filename, slugify
from tavola.design import DesignPlan
from tavola.judge import VisualScore
from tavola.llm import LLMError
from tavola.measure import MeasureError
from tavola.quality import Issue
from tavola.themes import get_theme

BRIEF_PAYLOAD: dict[str, Any] = {
    "title": "Shade is infrastructure",
    "dek": "Street trees are cheaper than air conditioning.",
    "thesis": "Plant now for cooling in ten years.",
    "claims": [
        {"text": "Trees cut peak street heat by 4.2°C.", "value": "4.2°C", "label": "cooling"},
        {"text": "One tree intercepts 1,400 litres of rain a year.", "value": "1,400 L", "label": "rain"},
        {"text": "Cover fell from 29% to 21% in a decade.", "value": "8 points", "label": "lost cover"},
        {"text": "Residents report fewer heat-illness days."},
        {"text": "Upkeep costs less than new air conditioning."},
    ],
    "relationships": [],
    "bottom_line": "Fund shade like infrastructure.",
    "citations": ["City survey 2024"],
}

PLAN_PAYLOAD: dict[str, Any] = {
    "layout": "hero-stat",
    "style": "professional",
    "orientation": "portrait",
    "density": "standard",
    "emphasis": [0],
    "rationale": "One strong number.",
}


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def json(self, messages, *, schema, **kwargs):  # type: ignore[no-untyped-def]
        if schema is Brief:
            return BRIEF_PAYLOAD
        return PLAN_PAYLOAD

    def complete(self, messages, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("short sources should not be condensed")


def _config() -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["design"]["style"] = "professional"
    return config


def test_generate_from_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "get_provider", lambda settings: FakeProvider())
    result = core.generate_from_text("A short source about trees.", config=_config())

    assert isinstance(result, GenerateResult)
    assert result.brief.title == "Shade is infrastructure"
    assert result.plan.layout == "hero-stat"
    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert result.width == 1080
    assert result.height == 1350
    assert result.quality.passed
    assert "Shade is infrastructure" in result.html


def test_generate_from_brief_skips_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "get_provider", lambda settings: FakeProvider())
    brief = Brief.model_validate(BRIEF_PAYLOAD)
    result = core.generate_from_brief(
        brief,
        config=_config(),
        source_title="saved-brief",
        source_origin="saved-brief.json",
    )
    assert result.brief is brief
    assert result.plan.layout == "hero-stat"
    assert result.source_title == "saved-brief"
    assert result.source_origin == "saved-brief.json"
    assert result.quality.passed


def test_measured_gate_blocks_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "get_provider", lambda settings: FakeProvider())
    measured = SimpleNamespace(
        issues=[Issue("overflow", "An element extends beyond the page.")],
        metrics={"overflow": []},
    )
    monkeypatch.setattr(core, "measure_html", lambda *args, **kwargs: measured)

    with pytest.raises(GenerateError, match="measured quality gate"):
        core.generate_from_text("A short source about trees.", config=_config())


def test_measured_gate_skips_without_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core, "get_provider", lambda settings: FakeProvider())

    def unavailable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise MeasureError("no browser")

    monkeypatch.setattr(core, "measure_html", unavailable)
    result = core.generate_from_text("A short source about trees.", config=_config())

    assert any("Measured checks skipped" in warning for warning in result.warnings)
    assert result.quality.passed


def test_reflow_retries_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core, "get_provider", lambda settings: FakeProvider())
    overflow = SimpleNamespace(
        issues=[Issue("overflow", "An element extends beyond the page.")],
        metrics={"overflow": [{"el": "div"}]},
    )
    clean = SimpleNamespace(issues=[], metrics={"min_font_px": 11.2})
    responses = iter([overflow, clean])
    monkeypatch.setattr(core, "measure_html", lambda *args, **kwargs: next(responses))

    result = core.generate_from_text("A short source about trees.", config=_config())

    assert any("reflowed" in warning for warning in result.warnings)
    assert result.measurements == {"min_font_px": 11.2}
    assert "padding: 2.6rem 2.8rem 2rem" in result.html


def test_slugify_and_default_filename() -> None:
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("!!!") == "tavola"
    result = GenerateResult(
        brief=Brief.model_validate(BRIEF_PAYLOAD),
        plan=DesignPlan.model_validate(PLAN_PAYLOAD),
        theme=get_theme("professional"),
        html="",
        quality=core.check_html("<h1 class=\"title\">x</h1>"),
    )
    assert default_filename(result) == "shade-is-infrastructure.png"


def test_save_html_and_sidecar(tmp_path: Path) -> None:
    result = GenerateResult(
        brief=Brief.model_validate(BRIEF_PAYLOAD),
        plan=DesignPlan.model_validate(PLAN_PAYLOAD),
        theme=get_theme("professional"),
        html="<!DOCTYPE html><html><body><h1 class=\"title\">X</h1></body></html>",
        quality=core.check_html('<h1 class="title">X</h1>'),
        warnings=["a warning"],
    )
    saved = core.save_result(result, tmp_path / "page.html", config=_config())

    assert saved.artefact.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert saved.html == saved.artefact
    payload = json.loads(saved.sidecar.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == 2
    assert payload["app"] == "tavola"
    assert payload["plan"]["layout"] == "hero-stat"
    assert payload["brief"]["title"] == "Shade is infrastructure"
    assert payload["warnings"] == ["a warning"]
    assert payload["render"]["width"] == 1080


def test_save_rejects_unknown_format(tmp_path: Path) -> None:
    result = GenerateResult(
        brief=Brief.model_validate(BRIEF_PAYLOAD),
        plan=DesignPlan.model_validate(PLAN_PAYLOAD),
        theme=get_theme("professional"),
        html="",
        quality=core.check_html('<h1 class="title">X</h1>'),
    )
    with pytest.raises(core.GenerateError):
        core.save_result(result, tmp_path / "page.jpg", config=_config())


def _three_plans() -> list[DesignPlan]:
    base = DesignPlan.model_validate(PLAN_PAYLOAD)
    return [
        base.model_copy(update={"density": density})
        for density in ("concise", "standard", "detailed")
    ]


def test_best_of_three_keeps_the_highest_vision_score(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(core, "get_provider", lambda settings: FakeProvider())
    plans = _three_plans()
    monkeypatch.setattr(core, "choose_plans", lambda *args, **kwargs: (plans, []))

    def measured(*args, **kwargs):  # type: ignore[no-untyped-def]
        assert kwargs.get("screenshot") is True
        return SimpleNamespace(
            issues=[],
            metrics={"min_font_px": 12.0},
            screenshot=b"png",
        )

    monkeypatch.setattr(core, "measure_html", measured)
    scores = iter([5.0, 9.0, 7.0])

    def fake_score(brief, plan, image, llm):  # type: ignore[no-untyped-def]
        assert image == b"png"
        value = next(scores)
        return VisualScore(
            legibility=value, composition=value, hierarchy=value
        )

    monkeypatch.setattr(core, "score_page", fake_score)
    config = _config()
    config["design"]["candidates"] = 3

    result = core.generate_from_brief(
        Brief.model_validate(BRIEF_PAYLOAD), config=config
    )

    assert result.plan.density == "standard"
    assert [candidate.score for candidate in result.candidates] == [50.0, 90.0, 70.0]
    assert all(candidate.score_source == "vision" for candidate in result.candidates)

    saved = core.save_result(result, tmp_path / "page.html", config=config)
    payload = json.loads(saved.sidecar.read_text(encoding="utf-8"))
    assert [item["score"] for item in payload["design"]["candidates"]] == [
        50.0,
        90.0,
        70.0,
    ]


def test_best_of_three_falls_back_when_vision_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core, "get_provider", lambda settings: FakeProvider())
    monkeypatch.setattr(
        core, "choose_plans", lambda *args, **kwargs: (_three_plans(), [])
    )
    monkeypatch.setattr(
        core,
        "measure_html",
        lambda *args, **kwargs: SimpleNamespace(
            issues=[], metrics={"min_font_px": 12.0}, screenshot=b"png"
        ),
    )

    def no_vision(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise LLMError("model does not accept images")

    monkeypatch.setattr(core, "score_page", no_vision)
    config = _config()
    config["design"]["candidates"] = 3

    result = core.generate_from_brief(
        Brief.model_validate(BRIEF_PAYLOAD), config=config
    )

    assert result.plan.density == "concise"
    assert any("Vision scoring failed" in warning for warning in result.warnings)
