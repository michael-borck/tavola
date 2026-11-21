"""Layered configuration for Tavola.

Layers, later wins:

1. Built-in defaults
2. ``~/.tavola.yaml``  — provider keys and machine defaults, set once
3. ``./tavola.yaml``   — per-directory overrides (or an explicit ``--config``)
4. CLI flags           — applied by the CLI on top of the loaded config

Secrets are referenced as ``${VAR}`` and expanded from the environment, so no
plaintext keys need to live in config files.
"""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path
from typing import Any

import yaml

# Exact pixel sizes. ``portrait`` is 4:5, the format NotebookLM uses for
# phone-friendly summaries; ``landscape`` is 16:9 for slides and docs.
ORIENTATIONS: dict[str, tuple[int, int]] = {
    "square": (1080, 1080),
    "portrait": (1080, 1350),
    "landscape": (1600, 900),
}

DENSITIES = ("concise", "standard", "detailed")


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""


DEFAULT_CONFIG: dict[str, Any] = {
    "llm": "ollama",
    "llms": {
        "ollama": {
            "base_url": "http://127.0.0.1:11434",
            "model": "qwen3.5:4b",
            "think": False,
            "timeout": 300,
        },
        "openai-compatible": {
            "base_url": "https://api.openai.com/v1",
            "model": None,
            "api_key": None,
            "timeout": 180,
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com",
            "model": "gemini-2.5-flash",
            "api_key": None,
            "timeout": 180,
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com",
            "model": "claude-sonnet-4-5",
            "api_key": None,
            "timeout": 180,
        },
        "tev": {
            "type": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "tev1:4b",
            "timeout": 60,
        },
    },
    "design": {
        "mode": "structured",
        "layout": "auto",
        "style": "professional",
        "orientation": "portrait",
        "density": "standard",
        "candidates": 1,
        "judge": "auto",
        "router": "off",
    },
    "illustration": {
        "provider": "off",
        "model": "gemini-2.5-flash-image",
        "preset": "editorial",
        "direction": "",
        "cache_dir": "~/.cache/tavola/assets",
        "timeout": 180,
    },
    "render": {
        "scale": 2,
        "measure": True,
    },
    "serve": {
        "host": "127.0.0.1",
        "port": 5827,
        "out_dir": "~/Pictures/Tavola",
    },
}

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

_ENV_OVERRIDES: dict[str, str] = {
    "llm": "TAVOLA_LLM",
}

_DESIGN_ENV_OVERRIDES: dict[str, str] = {
    "layout": "TAVOLA_LAYOUT",
    "style": "TAVOLA_STYLE",
    "mode": "TAVOLA_MODE",
    "orientation": "TAVOLA_ORIENTATION",
    "density": "TAVOLA_DENSITY",
    "candidates": "TAVOLA_CANDIDATES",
    "judge": "TAVOLA_JUDGE",
    "router": "TAVOLA_ROUTER",
}

_SERVE_ENV_OVERRIDES: dict[str, str] = {
    "host": "TAVOLA_HOST",
    "port": "TAVOLA_PORT",
    "out_dir": "TAVOLA_OUT_DIR",
}

_STANDARD_KEY_ENV: dict[str, str] = {
    "openai-compatible": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

_LLM_ENV_OVERRIDES: dict[str, dict[str, str]] = {
    "ollama": {
        "base_url": "TAVOLA_OLLAMA_URL",
        "model": "TAVOLA_OLLAMA_MODEL",
        "think": "TAVOLA_OLLAMA_THINK",
    },
    "openai-compatible": {
        "base_url": "TAVOLA_OPENAI_BASE_URL",
        "model": "TAVOLA_OPENAI_MODEL",
        "api_key": "TAVOLA_OPENAI_API_KEY",
    },
    "gemini": {
        "model": "TAVOLA_GEMINI_MODEL",
        "api_key": "TAVOLA_GEMINI_API_KEY",
    },
    "anthropic": {
        "model": "TAVOLA_ANTHROPIC_MODEL",
        "api_key": "TAVOLA_ANTHROPIC_API_KEY",
    },
}


def expand_env_vars(value: Any) -> Any:
    """Recursively expand ``${VAR}`` references in configuration values."""
    if isinstance(value, str):
        return _ENV_VAR_RE.sub(lambda m: os.getenv(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value


def _first_existing(*candidates: Path) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def find_home_config() -> Path | None:
    """The user-level config (~/.tavola.yaml)."""
    return _first_existing(
        Path.home() / ".tavola.yaml",
        Path.home() / ".tavola.yml",
    )


def find_project_config() -> Path | None:
    """The directory-level config (./tavola.yaml)."""
    return _first_existing(
        Path("./tavola.yaml"),
        Path("./tavola.yml"),
    )


def _read_config_file(config_file: Path) -> dict[str, Any] | None:
    try:
        with open(config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in {config_file}: {e}") from e
    except OSError as e:
        raise ConfigurationError(f"Error reading {config_file}: {e}") from e
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"Config file {config_file} must contain a YAML mapping"
        )
    return data


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two config dicts (override wins)."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration by layering defaults, home, and project files."""
    config = copy.deepcopy(DEFAULT_CONFIG)

    sources: list[Path] = []
    if home_config := find_home_config():
        sources.append(home_config)
    if config_path:
        explicit = Path(config_path)
        if not explicit.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        sources.append(explicit)
    elif project_config := find_project_config():
        sources.append(project_config)

    for source in sources:
        file_config = _read_config_file(source)
        if file_config:
            config = merge_configs(config, file_config)

    return expand_env_vars(config)


def _env_value(env_name: str) -> str | None:
    value = os.getenv(env_name)
    return value if value not in (None, "") else None


def _as_float(value: Any, name: str, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        raise ConfigurationError(f"{name} must be a number (got {value!r})") from e


def _as_bool(value: Any, name: str, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "on", "1"}:
            return True
        if lowered in {"false", "no", "off", "0"}:
            return False
    raise ConfigurationError(f"{name} must be true or false (got {value!r})")


def _as_int(value: Any, name: str, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise ConfigurationError(f"{name} must be an integer (got {value!r})") from e


def resolve_llm_settings(
    config: dict[str, Any],
    *,
    provider_label: str | None = None,
    global_overrides: bool = True,
) -> dict[str, Any]:
    """Effective settings for an LLM provider.

    Top-level ``model``, ``base_url``, and ``api_key`` act as overrides, so a
    one-off CLI flag or environment variable wins over the provider block. Pass
    ``global_overrides=False`` to resolve a judge provider without applying the
    writer's one-off flags.
    """
    label = provider_label or _env_value("TAVOLA_LLM") or str(
        config.get("llm") or "ollama"
    )
    blocks = config.get("llms")
    if not isinstance(blocks, dict):
        blocks = {}
    block = blocks.get(label)
    if not isinstance(block, dict):
        block = {}

    settings: dict[str, Any] = {
        "provider": label,
        "type": block.get("type") or label,
        "base_url": block.get("base_url"),
        "model": block.get("model"),
        "api_key": block.get("api_key"),
        "think": block.get("think", False),
        "timeout": block.get("timeout", 180),
    }
    for key, env_name in _LLM_ENV_OVERRIDES.get(label, {}).items():
        value = _env_value(env_name)
        if value is not None:
            settings[key] = value
    standard_key = _STANDARD_KEY_ENV.get(label)
    if standard_key and not settings.get("api_key"):
        value = _env_value(standard_key)
        if value is not None:
            settings["api_key"] = value

    if global_overrides:
        for key in ("base_url", "model", "api_key"):
            if config.get(key):
                settings[key] = config[key]
        for key, env_name in (
            ("model", "TAVOLA_MODEL"),
            ("base_url", "TAVOLA_BASE_URL"),
            ("api_key", "TAVOLA_API_KEY"),
        ):
            value = _env_value(env_name)
            if value is not None:
                settings[key] = value

    if not settings.get("base_url"):
        raise ConfigurationError(
            f"No base_url for LLM provider {label!r}. Set llms.{label}.base_url "
            "in ~/.tavola.yaml (run 'tavola --init-config' for a template)."
        )
    settings["base_url"] = str(settings["base_url"]).rstrip("/")
    settings["timeout"] = _as_float(
        settings.get("timeout"), f"llms.{label}.timeout", 180.0
    )
    settings["think"] = _as_bool(
        settings.get("think"), f"llms.{label}.think", False
    )
    model = str(settings.get("model") or "").strip()
    settings["model"] = model or None
    settings["api_key"] = settings.get("api_key") or None
    return settings


def resolve_design_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Effective defaults for the design pass."""
    design = dict(DEFAULT_CONFIG["design"])
    configured = config.get("design")
    if isinstance(configured, dict):
        design = merge_configs(design, configured)
    for key, env_name in _DESIGN_ENV_OVERRIDES.items():
        value = _env_value(env_name)
        if value is not None:
            design[key] = value

    orientation = str(design.get("orientation") or "portrait")
    if orientation not in ORIENTATIONS:
        raise ConfigurationError(
            f"design.orientation must be one of {', '.join(ORIENTATIONS)} "
            f"(got {orientation!r})"
        )
    density = str(design.get("density") or "standard")
    if density not in DENSITIES:
        raise ConfigurationError(
            f"design.density must be one of {', '.join(DENSITIES)} (got {density!r})"
        )
    design["orientation"] = orientation
    design["density"] = density
    mode = str(design.get("mode") or "structured")
    if mode not in {"structured", "illustrated", "auto"}:
        raise ConfigurationError(
            "design.mode must be structured, illustrated, or auto "
            f"(got {mode!r})"
        )
    design["mode"] = mode
    design["layout"] = str(design.get("layout") or "auto")
    design["style"] = str(design.get("style") or "professional")
    design["candidates"] = max(
        1, min(5, _as_int(design.get("candidates"), "design.candidates", 1))
    )
    design["judge"] = str(design.get("judge") or "auto").strip() or "auto"
    design["router"] = str(design.get("router") or "off").strip() or "off"
    return design


def resolve_illustration_settings(config: dict[str, Any]) -> dict[str, Any]:
    illustration = dict(DEFAULT_CONFIG["illustration"])
    configured = config.get("illustration")
    if isinstance(configured, dict):
        illustration = merge_configs(illustration, configured)
    provider = str(illustration.get("provider") or "off")
    if provider not in {"off", "gemini"}:
        raise ConfigurationError(
            "illustration.provider must be off or gemini "
            f"(got {provider!r})"
        )
    illustration["provider"] = provider
    illustration["model"] = str(
        illustration.get("model") or "gemini-2.5-flash-image"
    )
    from tavola.assets import ILLUSTRATION_STYLES

    preset = str(illustration.get("preset") or "editorial")
    if preset not in ILLUSTRATION_STYLES:
        raise ConfigurationError(
            f"illustration.preset must be one of "
            f"{', '.join(sorted(ILLUSTRATION_STYLES))} (got {preset!r})"
        )
    illustration["preset"] = preset
    illustration["direction"] = str(illustration.get("direction") or "").strip()
    illustration["style"] = ILLUSTRATION_STYLES[preset].prompt
    illustration["cache_dir"] = str(
        Path(os.path.expanduser(str(
            illustration.get("cache_dir") or "~/.cache/tavola/assets"
        )))
    )
    illustration["timeout"] = _as_float(
        illustration.get("timeout"), "illustration.timeout", 180.0
    )
    return illustration


def resolve_render_settings(config: dict[str, Any]) -> dict[str, Any]:
    render = dict(DEFAULT_CONFIG["render"])
    configured = config.get("render")
    if isinstance(configured, dict):
        render = merge_configs(render, configured)
    render["scale"] = max(1, _as_int(render.get("scale"), "render.scale", 2))
    render["measure"] = render.get("measure", True) is not False
    return render


def resolve_serve_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Effective web-server settings."""
    serve = dict(DEFAULT_CONFIG["serve"])
    configured = config.get("serve")
    if isinstance(configured, dict):
        serve = merge_configs(serve, configured)
    for key, env_name in _SERVE_ENV_OVERRIDES.items():
        value = _env_value(env_name)
        if value is not None:
            serve[key] = value
    out_dir = serve.get("out_dir") or "~/Pictures/Tavola"
    serve["out_dir"] = str(Path(os.path.expanduser(str(out_dir))))
    serve["port"] = _as_int(serve.get("port"), "serve.port", 5827)
    serve["host"] = str(serve.get("host") or "127.0.0.1")
    return serve


EXAMPLE_CONFIG = """\
# Tavola configuration
#
# Layered, later wins:
#   1. built-in defaults
#   2. ~/.tavola.yaml   (provider + keys, set once)
#   3. ./tavola.yaml    (per-directory overrides; or pass --config FILE)
#   4. CLI flags
#
# Secrets: reference environment variables as ${VAR} — no plaintext keys.

# Which model does the thinking: ollama | openai-compatible | gemini | anthropic
llm: ollama

llms:
  ollama:                      # local, no key, the default
    base_url: http://127.0.0.1:11434
    model: qwen3.5:4b          # any chat model; check `ollama list`
    think: false               # stop reasoning models hiding output in `thinking`
    timeout: 300

  openai-compatible:           # OpenAI, LM Studio, llama.cpp, OpenRouter, ...
    base_url: https://api.openai.com/v1
    model: gpt-4o-mini
    # api_key: "${OPENAI_API_KEY}"
    timeout: 180

  gemini:
    model: gemini-2.5-flash
    # api_key: "${GEMINI_API_KEY}"
    timeout: 180

  anthropic:
    model: claude-sonnet-4-5
    # api_key: "${ANTHROPIC_API_KEY}"
    timeout: 180

  tev:                         # local decision model, no key; used by the router
    type: ollama
    base_url: http://127.0.0.1:11434
    model: tev1:4b
    timeout: 60

design:
  mode: structured             # structured | illustrated | auto
  layout: auto                 # or an id from `tavola layouts`
  style: professional          # professional | scientific | editorial | sketch
  orientation: portrait        # square | portrait | landscape
  density: standard            # concise | standard | detailed
  candidates: 1                # 3 = best-of-3 variants scored by a vision model
  judge: auto                  # auto (same provider), none, or a provider label
  router: off                  # off | auto | tev (local System One decision model)

illustration:
  provider: off                # off | gemini (text-free hero art)
  model: gemini-2.5-flash-image
  preset: editorial            # editorial | clay | sketch | minimal
  direction: ""                # optional art direction; text is still forbidden
  cache_dir: ~/.cache/tavola/assets
  timeout: 180

render:
  scale: 2                     # 2 = 2160px wide for portrait; 1 is faster
  measure: true                # browser checks: overflow, type size, contrast

serve:
  host: 127.0.0.1
  port: 5827
  # v0.1 refuses non-loopback hosts; authenticated remote mode comes later.
  out_dir: ~/Pictures/Tavola
"""


def save_example_config(path: str = "tavola.yaml") -> Path:
    """Write an example configuration file and return its path."""
    target = Path(path)
    if target.exists():
        raise ConfigurationError(f"Refusing to overwrite existing {target}")
    target.write_text(EXAMPLE_CONFIG, encoding="utf-8")
    return target
