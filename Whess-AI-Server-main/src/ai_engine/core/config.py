from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class AgentConfigError(RuntimeError):
    """Raised when the multi-agent LLM configuration is incomplete."""


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class AgentSettings:
    api_key: str
    base_url: str
    model_name: str
    timeout_seconds: float = 30.0
    max_retries: int = 2
    temperature: float = 0.2
    json_mode: bool = True

    @classmethod
    def from_env(cls, load_env_file: bool = True) -> "AgentSettings":
        if load_env_file:
            load_dotenv()

        api_key = os.getenv("LLM_AGENT_API_KEY", "").strip()
        base_url = os.getenv("LLM_AGENT_BASE_URL", "").strip().rstrip("/")
        model_name = os.getenv("LLM_AGENT_MODEL", "").strip()

        if not base_url:
            raise AgentConfigError("Missing LLM_AGENT_BASE_URL.")
        if not model_name:
            raise AgentConfigError("Missing LLM_AGENT_MODEL.")

        return cls(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            timeout_seconds=float(os.getenv("LLM_AGENT_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.getenv("LLM_AGENT_MAX_RETRIES", "2")),
            temperature=float(os.getenv("LLM_AGENT_TEMPERATURE", "0.2")),
            json_mode=_as_bool(os.getenv("LLM_AGENT_JSON_MODE"), True),
        )
