"""CLI surface: default group, catalog commands, init config."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tavola.cli import app

runner = CliRunner()


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def json(self, messages, *, schema, **kwargs):  # type: ignore[no-untyped-def]
        return {
            "layout": "statement",
            "style": "scientific",
            "orientation": "square",
            "density": "concise",
            "emphasis": [0],
            "rationale": "Quote-led.",
        }

    def models(self) -> list[str]:
        return ["fake-model", "other-model"]


BRIEF_PAYLOAD: dict[str, Any] = {
    "title": "A saved brief",
    "dek": "One sentence of context.",
    "thesis": "The argument.",
    "claims": [
        {"text": "One claim."},
        {"text": "Two claims."},
        {"text": "Three claims."},
    ],
    "quote": "A line worth setting large.",
    "bottom_line": "The takeaway.",
    "citations": ["p. 1"],
}


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "tavola 0.1.0" in result.output


def test_layouts_command_lists_catalog() -> None:
    result = runner.invoke(app, ["layouts"])
    assert result.exit_code == 0
    for layout_id in ("bento", "hero-stat", "timeline", "comparison"):
        assert layout_id in result.output


def test_styles_command_lists_themes() -> None:
    result = runner.invoke(app, ["styles"])
    assert result.exit_code == 0
    for style in ("professional", "scientific", "editorial", "sketch"):
        assert style in result.output


def test_formats_command() -> None:
    result = runner.invoke(app, ["formats"])
    assert result.exit_code == 0
    assert "portrait" in result.output
    assert "1080 × 1350" in result.output


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_init_config_writes_file_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    first = runner.invoke(app, ["--init-config"])
    assert first.exit_code == 0
    assert "Wrote" in first.output
    second = runner.invoke(app, ["--init-config"])
    assert second.exit_code == 1
    assert "Refusing" in second.output


def test_bad_config_path_exits_nonzero() -> None:
    result = runner.invoke(
        app, ["generate", "anything.txt", "--config", "/no/such/tavola.yaml"]
    )
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_generate_help_mentions_variants() -> None:
    result = runner.invoke(app, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--candidates" in result.output
    assert "--judge" in result.output
    assert "--router" in result.output
    assert "--mode" in result.output
    assert "--illustration-style" in result.output


def test_health_prints_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "provider" in result.output
    assert "playwright" in result.output


def test_models_lists_provider_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("tavola.cli.get_provider", lambda settings: FakeProvider())
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "fake-model" in result.output
    assert "other-model" in result.output


def test_generate_from_saved_brief(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TAVOLA_MODE", "structured")
    monkeypatch.setattr(
        "tavola.core.get_provider", lambda settings: FakeProvider()
    )
    brief_path = tmp_path / "brief.json"
    brief_path.write_text(json.dumps(BRIEF_PAYLOAD), encoding="utf-8")
    output = tmp_path / "page.html"

    result = runner.invoke(app, ["--brief", str(brief_path), "-o", str(output)])

    assert result.exit_code == 0, result.output
    assert output.exists()
    assert (tmp_path / "page.json").exists()
    assert "A saved brief" in output.read_text(encoding="utf-8")
    sidecar = json.loads((tmp_path / "page.json").read_text(encoding="utf-8"))
    assert sidecar["source"]["origin"] == str(brief_path)


def test_brief_requires_source_or_file() -> None:
    result = runner.invoke(app, ["generate"])
    assert result.exit_code == 1
    assert "Give a source or --brief" in result.output


def test_serve_passes_out_dir_and_parent_pid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_server(config, *, host, port, parent_pid):  # type: ignore[no-untyped-def]
        captured.update(
            config=config, host=host, port=port, parent_pid=parent_pid
        )

    monkeypatch.setattr("tavola.serve.run_server", fake_run_server)
    out = tmp_path / "out"
    result = runner.invoke(
        app, ["serve", "--out-dir", str(out), "--parent-pid", "4242"]
    )

    assert result.exit_code == 0, result.output
    assert captured["parent_pid"] == 4242
    assert captured["config"]["serve"]["out_dir"] == str(out)
