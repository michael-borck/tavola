"""Google Gemini (Generative Language API)."""

from __future__ import annotations

import base64
from typing import Any

import requests
from pydantic import BaseModel

from tavola.llm.base import LLMError, LLMProvider, LLMResult, Message

_UNSUPPORTED = {
    "$defs",
    "title",
    "default",
    "additionalProperties",
    "discriminator",
    "examples",
}


def _gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Resolve $refs and reduce a Pydantic schema to Gemini's OpenAPI subset."""
    defs = schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, list):
            return [resolve(item) for item in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            name = str(node["$ref"]).rsplit("/", 1)[-1]
            target = defs.get(name)
            return resolve(target) if target is not None else {"type": "object"}
        if "anyOf" in node:
            options = [opt for opt in node["anyOf"] if opt.get("type") != "null"]
            if len(options) == 1:
                merged = resolve(options[0])
                if isinstance(merged, dict):
                    merged["nullable"] = True
                return merged
            return {"anyOf": [resolve(opt) for opt in options]}
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                out["properties"] = {
                    name: resolve(prop) for name, prop in value.items()
                }
                continue
            if key in _UNSUPPORTED:
                continue
            if key == "type" and value == "null":
                continue
            out[key] = resolve(value)
        return out

    result = resolve(schema)
    return result if isinstance(result, dict) else {"type": "object"}


class GeminiProvider(LLMProvider):
    name = "gemini"

    def _key(self) -> str:
        if not self.api_key:
            raise LLMError(
                "No Gemini API key. Set llms.gemini.api_key or GEMINI_API_KEY."
            )
        return str(self.api_key)

    def _split(
        self, messages: list[Message], images: list[bytes] | None = None
    ) -> tuple[str | None, list[dict[str, Any]]]:
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "user")
            text = message.get("content", "")
            if role == "system":
                system_parts.append(text)
                continue
            contents.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": text}],
                }
            )
        if images:
            for content in reversed(contents):
                if content["role"] != "user":
                    continue
                parts = content["parts"]
                for image in images:
                    parts.append(
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": base64.b64encode(image).decode("ascii"),
                            }
                        }
                    )
                break
        system = "\n\n".join(system_parts) or None
        return system, contents

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
        system, contents = self._split(messages, images)
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if not self.settings.get("think", False) and "2.5" in model:
            body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
        if schema is not None:
            body["generationConfig"]["responseMimeType"] = "application/json"
            body["generationConfig"]["responseSchema"] = _gemini_schema(
                schema.model_json_schema()
            )

        try:
            response = requests.post(
                f"{self.base_url}/v1beta/models/{model}:generateContent",
                params={"key": self._key()},
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise LLMError(f"Could not reach Gemini: {e}") from e
        if response.status_code >= 400:
            raise LLMError(
                f"Gemini returned {response.status_code}: "
                f"{response.text.strip() or response.reason}"
            )
        data = response.json()
        candidates = data.get("candidates") if isinstance(data, dict) else None
        text = ""
        if candidates and isinstance(candidates, list):
            candidate = candidates[0] if isinstance(candidates[0], dict) else {}
            content = candidate.get("content") if isinstance(candidate, dict) else {}
            parts = content.get("parts") if isinstance(content, dict) else None
            if isinstance(parts, list):
                text = "".join(
                    str(part.get("text") or "")
                    for part in parts
                    if isinstance(part, dict)
                )
        text = text.strip()
        if not text:
            raise LLMError("Gemini returned an empty completion.")
        return LLMResult(text=text, provider=self.name, model=model)

    def models(self) -> list[str]:
        try:
            response = requests.get(
                f"{self.base_url}/v1beta/models",
                params={"key": self._key()},
                timeout=30,
            )
        except requests.RequestException as e:
            raise LLMError(f"Could not reach Gemini: {e}") from e
        if response.status_code >= 400:
            raise LLMError(
                f"Gemini returned {response.status_code}: "
                f"{response.text.strip() or response.reason}"
            )
        data = response.json()
        items = data.get("models") if isinstance(data, dict) else None
        names: list[str] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            if name:
                names.append(name.removeprefix("models/"))
        return names
