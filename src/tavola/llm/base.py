"""Provider abstraction: messages in, text (or JSON) out.

Every backend is a thin client over one API. Providers raise ``LLMError`` on
failure; Tavola reports it and exits non-zero rather than inventing content.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


class LLMError(Exception):
    """Raised when a provider cannot return a usable completion."""


Message = dict[str, Any]


@dataclass
class LLMResult:
    """One completion plus what produced it."""

    text: str
    provider: str
    model: str | None = None


def extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from a model reply, tolerating fences and prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise LLMError(
                "The model did not return JSON. Check the model and the "
                "provider's structured-output support."
            ) from None
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as e:
            raise LLMError(f"The model returned invalid JSON: {e}") from None
    if not isinstance(value, dict):
        raise LLMError("The model returned JSON that is not an object.")
    return value


class LLMProvider(ABC):
    """One backend: turn a message list into one completion."""

    name = "base"

    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings
        self.base_url = str(settings.get("base_url") or "").rstrip("/")
        self.model = settings.get("model")
        self.api_key = settings.get("api_key")
        self.timeout = float(settings.get("timeout") or 180)

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        *,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        images: list[bytes] | None = None,
    ) -> LLMResult:
        """Return one completion. Raises LLMError on failure."""
        raise NotImplementedError

    def json(
        self,
        messages: list[Message],
        *,
        schema: type[BaseModel],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        images: list[bytes] | None = None,
    ) -> dict[str, Any]:
        """Ask for a structured reply and parse it."""
        result = self.complete(
            messages,
            schema=schema,
            temperature=temperature,
            max_tokens=max_tokens,
            images=images,
        )
        return extract_json(result.text)

    def models(self) -> list[str]:
        """Model names this backend reports. Raises LLMError if unsupported."""
        raise LLMError(f"Provider '{self.name}' cannot list models.")

    def resolve_model(self) -> str:
        if self.model:
            return str(self.model)
        raise LLMError(
            f"No model configured for provider '{self.name}'. Set "
            f"llms.{self.name}.model in ~/.tavola.yaml or pass --model."
        )
