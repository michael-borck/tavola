"""Tev/System One routing over ranked compositions."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tavola.brief import Brief, Claim
from tavola.compose import Composition
from tavola.router import RouterError, route_layout


def _brief() -> Brief:
    return Brief(
        title="T",
        dek="D",
        thesis="H",
        claims=[
            Claim(text="A", value="1"),
            Claim(text="B", value="2"),
            Claim(text="C", value="3"),
        ],
        bottom_line="B",
    )


def test_route_layout_posts_a_choice_question(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict = {}

    def fake_post(url, *, json, timeout):  # type: ignore[no-untyped-def]
        captured["url"] = url
        captured["body"] = json
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "answers": {
                    "layout": {
                        "type": "choice",
                        "choice": "bento",
                        "probabilities": {"stat-row": 0.2, "bento": 0.7},
                        "confidence": 0.5,
                    }
                },
                "usage": {"input_tokens": 10, "output_tokens": 0},
            },
        )

    monkeypatch.setattr("tavola.router.requests.post", fake_post)
    candidates = [
        Composition("stat-row", 10, "figures"),
        Composition("bento", 9, "mixed evidence"),
    ]
    decision = route_layout(
        _brief(),
        base_url="http://localhost:11434",
        model="tev1:4b",
        candidates=candidates,
    )
    assert captured["url"].endswith("/v1/systemone")
    assert captured["body"]["model"] == "tev1:4b"
    assert set(captured["body"]["questions"]["layout"]["criteria"]) == {
        "stat-row",
        "bento",
    }
    assert decision.layout == "bento"
    assert decision.probability == 0.7
    assert decision.usage["input_tokens"] == 10


def test_route_layout_rejects_unknown_choice(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def fake_post(url, *, json, timeout):  # type: ignore[no-untyped-def]
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "answers": {"layout": {"choice": "invented", "probabilities": {}}}
            },
        )

    monkeypatch.setattr("tavola.router.requests.post", fake_post)
    with pytest.raises(RouterError, match="unknown layout"):
        route_layout(
            _brief(),
            base_url="http://localhost:11434",
            model="tev1:4b",
            candidates=[
                Composition("stat-row", 10, "figures"),
                Composition("bento", 9, "mixed evidence"),
            ],
        )
