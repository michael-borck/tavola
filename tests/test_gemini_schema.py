"""Gemini's reduced JSON Schema keeps property names such as ``title``."""

from __future__ import annotations

from types import SimpleNamespace

from tavola.brief import Brief
from tavola.design import DesignPlan
from tavola.llm.gemini import GeminiProvider, _gemini_schema


def _required_fields(schema: dict) -> tuple[dict, list[str]]:
    assert isinstance(schema["properties"], dict)
    return schema["properties"], schema.get("required", [])


def test_brief_schema_keeps_title_property() -> None:
    schema = _gemini_schema(Brief.model_json_schema())
    properties, required = _required_fields(schema)
    assert "title" in properties
    assert all(name in properties for name in required)


def test_design_schema_required_fields_exist() -> None:
    schema = _gemini_schema(DesignPlan.model_json_schema())
    properties, required = _required_fields(schema)
    assert all(name in properties for name in required)


def test_gemini_disables_thinking_for_25_flash(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict = {}

    def fake_post(url, *, params, json, timeout):  # type: ignore[no-untyped-def]
        captured["body"] = json
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "candidates": [{"content": {"parts": [{"text": "{}"}]}}]
            },
        )

    monkeypatch.setattr("tavola.llm.gemini.requests.post", fake_post)
    provider = GeminiProvider(
        {
            "base_url": "https://example.test",
            "model": "gemini-2.5-flash",
            "api_key": "key",
            "think": False,
        }
    )
    provider.complete(
        [{"role": "user", "content": "hi"}],
        schema=DesignPlan,
    )
    assert captured["body"]["generationConfig"]["thinkingConfig"] == {
        "thinkingBudget": 0
    }
