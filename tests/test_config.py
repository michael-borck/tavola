"""Configuration layering and environment expansion."""

from __future__ import annotations

from pathlib import Path

import pytest

from tavola.config import (
    DEFAULT_CONFIG,
    ConfigurationError,
    expand_env_vars,
    load_config,
    merge_configs,
    resolve_design_settings,
    resolve_llm_settings,
    save_example_config,
)


def test_merge_configs_is_deep() -> None:
    base = {"llm": "ollama", "design": {"style": "professional", "density": "standard"}}
    override = {"design": {"density": "detailed"}}
    merged = merge_configs(base, override)
    assert merged["design"] == {"style": "professional", "density": "detailed"}
    assert base["design"]["density"] == "standard"


def test_expand_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_KEY", "secret")
    value = {"key": "${MY_KEY}", "missing": "${NOPE}", "list": ["${MY_KEY}"]}
    expanded = expand_env_vars(value)
    assert expanded == {"key": "secret", "missing": "", "list": ["secret"]}


def test_load_config_layers_home_and_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    (home / ".tavola.yaml").write_text("design:\n  style: editorial\n", encoding="utf-8")
    (project / "tavola.yaml").write_text("design:\n  density: detailed\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(project)

    config = load_config()
    assert config["design"]["style"] == "editorial"
    assert config["design"]["density"] == "detailed"
    assert config["llm"] == DEFAULT_CONFIG["llm"]


def test_resolve_design_rejects_bad_orientation() -> None:
    config = {"design": {"orientation": "wide"}}
    with pytest.raises(ConfigurationError):
        resolve_design_settings(config)


def test_resolve_design_rejects_bad_density() -> None:
    config = {"design": {"density": "verbose"}}
    with pytest.raises(ConfigurationError):
        resolve_design_settings(config)


def test_standard_api_key_env_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "standard-key")
    config = {
        "llm": "gemini",
        "llms": {"gemini": {"base_url": "https://example.test"}},
    }
    assert resolve_llm_settings(config)["api_key"] == "standard-key"
    monkeypatch.setenv("TAVOLA_GEMINI_API_KEY", "prefixed-key")
    assert resolve_llm_settings(config)["api_key"] == "prefixed-key"


def test_judge_provider_ignores_writer_overrides() -> None:
    config = {
        "llm": "ollama",
        "model": "writer-model",
        "llms": {
            "ollama": {"base_url": "http://localhost:11434", "model": "local"},
            "gemini": {
                "base_url": "https://example.test",
                "model": "gemini-judge",
            },
        },
    }
    writer = resolve_llm_settings(config)
    judge = resolve_llm_settings(
        config, provider_label="gemini", global_overrides=False
    )
    assert writer["model"] == "writer-model"
    assert judge["model"] == "gemini-judge"


def test_ollama_think_is_a_boolean(monkeypatch: pytest.MonkeyPatch) -> None:
    config = {"llm": "ollama", "llms": {"ollama": {"base_url": "http://x"}}}
    assert resolve_llm_settings(config)["think"] is False
    monkeypatch.setenv("TAVOLA_OLLAMA_THINK", "true")
    assert resolve_llm_settings(config)["think"] is True
    monkeypatch.setenv("TAVOLA_OLLAMA_THINK", "maybe")
    with pytest.raises(ConfigurationError):
        resolve_llm_settings(config)


def test_candidates_and_judge_defaults() -> None:
    design = resolve_design_settings({})
    assert design["mode"] == "structured"
    assert design["candidates"] == 1
    assert design["judge"] == "auto"
    assert design["router"] == "off"


def test_candidates_clamp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVOLA_CANDIDATES", "9")
    assert resolve_design_settings({})["candidates"] == 5
    monkeypatch.setenv("TAVOLA_CANDIDATES", "0")
    assert resolve_design_settings({})["candidates"] == 1


def test_illustration_defaults_and_validation() -> None:
    from tavola.config import resolve_illustration_settings

    assert resolve_illustration_settings({})["provider"] == "off"
    with pytest.raises(ConfigurationError):
        resolve_illustration_settings({"illustration": {"provider": "magic"}})
    with pytest.raises(ConfigurationError):
        resolve_illustration_settings({"illustration": {"preset": "anime"}})


def test_design_mode_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVOLA_MODE", "illustrated")
    assert resolve_design_settings({})["mode"] == "illustrated"
    monkeypatch.setenv("TAVOLA_MODE", "weird")
    with pytest.raises(ConfigurationError):
        resolve_design_settings({})


def test_router_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVOLA_ROUTER", "tev")
    assert resolve_design_settings({})["router"] == "tev"


def test_save_example_config_refuses_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "tavola.yaml"
    save_example_config(str(target))
    assert "llm: ollama" in target.read_text(encoding="utf-8")
    with pytest.raises(ConfigurationError):
        save_example_config(str(target))


def test_missing_explicit_config_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        load_config(str(tmp_path / "nope.yaml"))
