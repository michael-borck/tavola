"""Text-free hero asset generation and cache."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tavola.assets import AssetError, build_hero_prompt, generate_hero
from tavola.brief import Brief, Claim


def _brief() -> Brief:
    return Brief(
        title="Cooling cities",
        dek="Shade is cheaper than air conditioning.",
        thesis="Plant trees now.",
        claims=[Claim(text="A"), Claim(text="B"), Claim(text="C")],
        bottom_line="Fund shade.",
    )


def test_prompt_forbids_text() -> None:
    prompt = build_hero_prompt(
        _brief(), "flat editorial", "warm coastal palette, avoid people"
    )
    assert "no text" in prompt.lower()
    assert "Cooling cities" in prompt
    assert "warm coastal palette" in prompt
    assert "left 55%" in prompt


def test_generate_hero_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_post(url, *, params, json, timeout):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        assert json["generationConfig"]["responseModalities"] == ["IMAGE"]
        assert json["generationConfig"]["imageConfig"]["aspectRatio"] == "4:5"
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "candidates": [
                    {"content": {"parts": [{"inlineData": {"data": "cG5n"}}]}}
                ]
            },
        )

    monkeypatch.setattr("tavola.assets.requests.post", fake_post)
    illustration = {
        "provider": "gemini",
        "model": "gemini-2.5-flash-image",
        "style": "flat editorial",
        "cache_dir": str(tmp_path),
        "timeout": 10,
    }
    llm = {"base_url": "https://example.test", "api_key": "key"}
    assert generate_hero(_brief(), illustration=illustration, llm=llm) == b"png"
    assert generate_hero(_brief(), illustration=illustration, llm=llm) == b"png"
    assert calls == 1
    assert len(list(tmp_path.glob("*.png"))) == 1


def test_generate_hero_rejects_unknown_provider() -> None:
    with pytest.raises(AssetError):
        generate_hero(
            _brief(),
            illustration={"provider": "magic"},
            llm={"base_url": "x", "api_key": "y"},
        )


def test_illustration_style_catalog() -> None:
    from tavola.assets import ILLUSTRATION_STYLES

    assert set(ILLUSTRATION_STYLES) == {
        "cinematic",
        "clay",
        "editorial",
        "minimal",
        "papercut",
        "sketch",
    }
