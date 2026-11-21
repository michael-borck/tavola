"""Web app factory: page, meta, gallery, localhost guard."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tavola.config import DEFAULT_CONFIG, ConfigurationError
from tavola.serve import create_app, run_server


def _config(tmp_path: Path) -> dict[str, object]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    serve = config["serve"]
    assert isinstance(serve, dict)
    serve["out_dir"] = str(tmp_path / "out")
    return config


def test_index_serves_one_screen(tmp_path: Path) -> None:
    with TestClient(create_app(_config(tmp_path))) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "One source. One page." in response.text
    assert "Generate" in response.text
    assert "visual-styles" in response.text
    assert "Visual style" in response.text
    assert "cdn." not in response.text
    assert "googleapis" not in response.text


def test_meta_lists_catalog_and_defaults(tmp_path: Path) -> None:
    with TestClient(create_app(_config(tmp_path))) as client:
        meta = client.get("/api/meta").json()
    assert {layout["id"] for layout in meta["layouts"]} == {
        "antv-comparison",
        "antv-hierarchy",
        "antv-sequence",
        "bar-share",
        "bento",
        "donut-share",
        "comparison",
        "dashboard",
        "hero-stat",
        "hierarchy",
        "grouped-bars",
        "illustrated",
        "illustrated-comparison",
        "illustrated-quote",
        "illustrated-sequence",
        "illustrated-trend",
        "poster",
        "process",
        "quadrant",
        "statement",
        "stacked-share",
        "stat-row",
        "timeline",
        "trend",
        "trend-dashboard",
    }
    assert {style["id"] for style in meta["styles"]} == {
        "professional",
        "scientific",
        "editorial",
        "sketch",
        "noir",
        "warm",
    }
    assert meta["defaults"]["orientation"] == "portrait"
    assert {style["id"] for style in meta["illustration_styles"]} == {
        "cinematic",
        "clay",
        "editorial",
        "minimal",
        "papercut",
        "sketch",
    }
    assert meta["defaults"]["illustration"]["preset"] == "editorial"
    assert meta["provider"]["ready"] is True
    assert meta["provider"]["model"] == "qwen3.5:4b"


def test_preset_preview_is_served(tmp_path: Path) -> None:
    with TestClient(create_app(_config(tmp_path))) as client:
        response = client.get("/previews/editorial.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")


def test_gallery_starts_empty(tmp_path: Path) -> None:
    with TestClient(create_app(_config(tmp_path))) as client:
        assert client.get("/api/gallery").json() == []


def test_generate_requires_a_source(tmp_path: Path) -> None:
    with TestClient(create_app(_config(tmp_path))) as client:
        response = client.post("/api/generate", json={"text": " ", "url": ""})
    assert response.status_code == 400


def test_run_server_refuses_remote_bind() -> None:
    with pytest.raises(ConfigurationError):
        run_server(DEFAULT_CONFIG, host="0.0.0.0", port=5827)
