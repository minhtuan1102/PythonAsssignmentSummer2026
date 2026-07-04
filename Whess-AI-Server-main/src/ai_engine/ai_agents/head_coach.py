from __future__ import annotations

import json
from typing import Any, Mapping

from src.ai_engine.core.errors import AgentOutputError
from src.ai_engine.services.llm_client import LLMClient
from src.ai_engine.utils.json_utils import extract_json_object
from src.ai_engine.domain.schemas import DataMinerResult, TacticalReport


import os
from pathlib import Path
PROMPT_PATH = Path(__file__).parent / "prompts" / "head_coach.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()


class HeadCoachAgent:
    def __init__(self, llm_client: LLMClient, max_retries: int = 2):
        self.llm_client = llm_client
        self.max_retries = max_retries

    def run(self, mined: DataMinerResult, tactical_report: TacticalReport) -> str:
        payload = mined.to_coach_payload(tactical_report)
        user_message = json.dumps(payload, ensure_ascii=False, indent=2)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            raw_response = ""
            try:
                raw_response = self.llm_client.complete(messages)
                data = extract_json_object(raw_response)
                return self._parse_explanation(data)
            except Exception as exc:
                last_error = exc
                if raw_response:
                    messages.append({"role": "assistant", "content": raw_response})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "JSON trên chưa đúng schema. Hãy trả lại duy nhất "
                            "một JSON object với key explanation là string không rỗng."
                        ),
                    }
                )
                if attempt >= self.max_retries:
                    break

        raise AgentOutputError(f"Head Coach Agent failed: {last_error}")

    def _parse_explanation(self, data: Mapping[str, Any]) -> str:
        explanation = str(data.get("explanation") or "").strip()
        if not explanation:
            raise AgentOutputError("Head Coach output must contain explanation.")
        return explanation
