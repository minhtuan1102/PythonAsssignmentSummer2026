from __future__ import annotations

import json
from typing import Any

from src.ai_engine.errors import AgentOutputError


def extract_json_object(text: str) -> dict[str, Any]:
    clean_text = text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()

    try:
        value = json.loads(clean_text)
    except json.JSONDecodeError:
        start = clean_text.find("{")
        end = clean_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AgentOutputError("LLM response did not contain a JSON object.")
        value = json.loads(clean_text[start : end + 1])

    if not isinstance(value, dict):
        raise AgentOutputError("LLM response JSON must be an object.")
    return value
