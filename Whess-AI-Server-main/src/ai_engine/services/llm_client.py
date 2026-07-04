from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Mapping, Protocol, Sequence

from src.ai_engine.core.config import AgentSettings
from src.ai_engine.core.errors import LLMClientError


class LLMClient(Protocol):
    def complete(self, messages: Sequence[Mapping[str, str]]) -> str:
        """Return the assistant message content for a chat request."""


class OpenAICompatibleLLMClient:
    """Minimal OpenAI-compatible chat completions client.

    Works with endpoints shaped like:
    POST {LLM_AGENT_BASE_URL}/chat/completions
    """

    def __init__(self, settings: AgentSettings):
        self.settings = settings
        self.endpoint = f"{settings.base_url}/chat/completions"

    def complete(self, messages: Sequence[Mapping[str, str]]) -> str:
        payload: dict[str, object] = {
            "model": self.settings.model_name,
            "messages": list(messages),
            "temperature": self.settings.temperature,
        }
        if self.settings.json_mode:
            payload["response_format"] = {"type": "json_object"}

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.settings.timeout_seconds
            ) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"LLM endpoint returned HTTP {exc.code}: {detail}")
        except urllib.error.URLError as exc:
            raise LLMClientError(f"Cannot reach LLM endpoint: {exc.reason}")

        try:
            data = json.loads(response_body)
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"Unexpected LLM response shape: {exc}")
