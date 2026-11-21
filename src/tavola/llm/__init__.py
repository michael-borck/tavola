"""Provider registry."""

from __future__ import annotations

from typing import Any

from tavola.llm.anthropic import AnthropicProvider
from tavola.llm.base import LLMError, LLMProvider, LLMResult, Message, extract_json
from tavola.llm.gemini import GeminiProvider
from tavola.llm.ollama import OllamaProvider
from tavola.llm.openai_compat import OpenAICompatibleProvider

PROVIDER_TYPES: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
    "openai-compatible": OpenAICompatibleProvider,
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
}


def get_provider(settings: dict[str, Any]) -> LLMProvider:
    """Build the provider named by ``settings['type']`` (or the label)."""
    kind = str(settings.get("type") or settings.get("provider") or "")
    provider_class = PROVIDER_TYPES.get(kind)
    if provider_class is None:
        choices = ", ".join(sorted(PROVIDER_TYPES))
        raise LLMError(f"Unknown LLM provider {kind!r}; choose one of {choices}.")
    return provider_class(settings)


__all__ = [
    "LLMError",
    "LLMProvider",
    "LLMResult",
    "Message",
    "PROVIDER_TYPES",
    "extract_json",
    "get_provider",
]
