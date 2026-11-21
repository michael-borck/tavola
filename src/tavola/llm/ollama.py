"""Native Ollama chat client.

Uses ``/api/chat`` rather than Ollama's OpenAI compatibility layer because the
native endpoint accepts a full JSON Schema through ``format``.
"""

from __future__ import annotations

import base64
from typing import Any

import requests
from pydantic import BaseModel

from tavola.llm.base import LLMError, LLMProvider, LLMResult, Message


class OllamaProvider(LLMProvider):
    name = "ollama"

    def complete(
        self,
        messages: list[Message],
        *,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        images: list[bytes] | None = None,
    ) -> LLMResult:
        model = self.resolve_model()
        prepared: list[Message] = [dict(message) for message in messages]
        if images:
            target: dict[str, Any] | None = next(
                (
                    message
                    for message in reversed(prepared)
                    if message.get("role") == "user"
                ),
                None,
            )
            if target is None:
                target = {"role": "user", "content": ""}
                prepared.append(target)
            target["images"] = [
                base64.b64encode(image).decode("ascii") for image in images
            ]
        body: dict[str, Any] = {
            "model": model,
            "messages": prepared,
            "stream": False,
            "think": bool(self.settings.get("think", False)),
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if schema is not None:
            body["format"] = schema.model_json_schema()
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise LLMError(
                f"Could not reach Ollama at {self.base_url}. Is it running? ({e})"
            ) from e
        if response.status_code >= 400:
            raise LLMError(
                f"Ollama returned {response.status_code}: "
                f"{response.text.strip() or response.reason}"
            )
        data = response.json()
        message = data.get("message") if isinstance(data, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        text = str(content or "").strip()
        if not text:
            raise LLMError("Ollama returned an empty completion.")
        return LLMResult(text=text, provider=self.name, model=model)

    def models(self) -> list[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=15)
        except requests.RequestException as e:
            raise LLMError(
                f"Could not reach Ollama at {self.base_url}. Is it running? ({e})"
            ) from e
        if response.status_code >= 400:
            raise LLMError(
                f"Ollama returned {response.status_code}: "
                f"{response.text.strip() or response.reason}"
            )
        data = response.json()
        items = data.get("models") if isinstance(data, dict) else None
        return [
            str(item["name"])
            for item in (items or [])
            if isinstance(item, dict) and item.get("name")
        ]
