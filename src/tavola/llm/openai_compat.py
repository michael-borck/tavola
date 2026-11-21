"""OpenAI-compatible chat completions.

Works with OpenAI, LM Studio, llama.cpp, OpenRouter, vLLM, and anything else
that exposes ``/v1/chat/completions``. ``base_url`` must include ``/v1`` where
the backend expects it.
"""

from __future__ import annotations

import base64
from typing import Any

import requests
from pydantic import BaseModel

from tavola.llm.base import LLMError, LLMProvider, LLMResult, Message


def _with_images(
    messages: list[Message], images: list[bytes] | None
) -> list[Message]:
    if not images:
        return messages
    prepared: list[Message] = [dict(message) for message in messages]
    target: dict[str, Any] | None = next(
        (message for message in reversed(prepared) if message.get("role") == "user"),
        None,
    )
    if target is None:
        target = {"role": "user", "content": ""}
        prepared.append(target)
    content = target.get("content", "")
    parts: list[dict[str, Any]]
    if isinstance(content, list):
        parts = [part for part in content if isinstance(part, dict)]
    else:
        parts = [{"type": "text", "text": str(content)}]
    for image in images:
        encoded = base64.b64encode(image).decode("ascii")
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded}"},
            }
        )
    target["content"] = parts
    return prepared


def _detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or response.reason
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        if error:
            return str(error)
    return response.text.strip() or response.reason


class OpenAICompatibleProvider(LLMProvider):
    name = "openai-compatible"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post(self, path: str, body: dict[str, Any]) -> requests.Response:
        try:
            return requests.post(
                f"{self.base_url}{path}",
                json=body,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise LLMError(
                f"Could not reach the LLM at {self.base_url}: {e}"
            ) from e

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
        body: dict[str, Any] = {
            "model": model,
            "messages": _with_images(messages, images),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Try the strongest structured-output mode first, then degrade. Some
        # servers reject json_schema, some reject response_format entirely.
        formats: list[dict[str, Any] | None] = [None]
        if schema is not None:
            formats = [
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "tavola_result",
                        "schema": schema.model_json_schema(),
                        "strict": False,
                    },
                },
                {"type": "json_object"},
                None,
            ]

        response: requests.Response | None = None
        for fmt in formats:
            if fmt is None:
                body.pop("response_format", None)
            else:
                body["response_format"] = fmt
            response = self._post("/chat/completions", body)
            if response.status_code < 400:
                break
            if response.status_code not in (400, 404, 422):
                raise LLMError(
                    f"LLM returned {response.status_code}: {_detail(response)}"
                )
        if response is None or response.status_code >= 400:
            detail = _detail(response) if response is not None else "no response"
            raise LLMError(f"LLM request failed: {detail}")

        data = response.json()
        choices = data.get("choices") if isinstance(data, dict) else None
        content: Any = ""
        if choices and isinstance(choices, list):
            first = choices[0] if isinstance(choices[0], dict) else {}
            message = first.get("message") if isinstance(first, dict) else {}
            if isinstance(message, dict):
                content = message.get("content") or ""
        if isinstance(content, list):
            content = " ".join(
                str(part.get("text") or "")
                for part in content
                if isinstance(part, dict)
            )
        text = str(content).strip()
        if not text:
            raise LLMError("The model returned an empty completion.")
        return LLMResult(text=text, provider=self.name, model=model)

    def models(self) -> list[str]:
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=min(self.timeout, 30),
            )
        except requests.RequestException as e:
            raise LLMError(
                f"Could not reach the LLM at {self.base_url}: {e}"
            ) from e
        if response.status_code >= 400:
            raise LLMError(
                f"Model list returned {response.status_code}: {_detail(response)}"
            )
        data = response.json()
        items = data.get("data") if isinstance(data, dict) else data
        names = [
            str(item["id"])
            for item in (items or [])
            if isinstance(item, dict) and item.get("id")
        ]
        return names
