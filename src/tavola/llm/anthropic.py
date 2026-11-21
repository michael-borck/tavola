"""Anthropic Messages API.

Structured output uses a single forced tool, which is the reliable JSON mode on
the Messages API.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import requests
from pydantic import BaseModel

from tavola.llm.base import LLMError, LLMProvider, LLMResult, Message


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise LLMError(
                "No Anthropic API key. Set llms.anthropic.api_key or "
                "ANTHROPIC_API_KEY."
            )
        return {
            "Content-Type": "application/json",
            "x-api-key": str(self.api_key),
            "anthropic-version": "2023-06-01",
        }

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
        system_parts: list[str] = []
        turns: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "user")
            text = message.get("content", "")
            if role == "system":
                system_parts.append(text)
                continue
            turns.append(
                {
                    "role": "assistant" if role == "assistant" else "user",
                    "content": text,
                }
            )

        if images:
            for turn in reversed(turns):
                if turn["role"] != "user":
                    continue
                text = turn["content"]
                image_blocks: list[dict[str, Any]] = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64.b64encode(image).decode("ascii"),
                        },
                    }
                    for image in images
                ]
                if text:
                    image_blocks.append({"type": "text", "text": text})
                turn["content"] = image_blocks
                break

        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": turns,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)
        if schema is not None:
            body["tools"] = [
                {
                    "name": "emit_result",
                    "description": "Return the structured Tavola result.",
                    "input_schema": schema.model_json_schema(),
                }
            ]
            body["tool_choice"] = {"type": "tool", "name": "emit_result"}

        try:
            response = requests.post(
                f"{self.base_url}/v1/messages",
                json=body,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise LLMError(f"Could not reach Anthropic: {e}") from e
        if response.status_code >= 400:
            raise LLMError(
                f"Anthropic returned {response.status_code}: "
                f"{response.text.strip() or response.reason}"
            )
        data = response.json()
        blocks = data.get("content") if isinstance(data, dict) else None
        if not isinstance(blocks, list):
            raise LLMError("Anthropic returned an unexpected response.")
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                return LLMResult(
                    text=json.dumps(block.get("input") or {}),
                    provider=self.name,
                    model=model,
                )
        text = "".join(
            str(block.get("text") or "")
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
        if not text:
            raise LLMError("Anthropic returned an empty completion.")
        return LLMResult(text=text, provider=self.name, model=model)
