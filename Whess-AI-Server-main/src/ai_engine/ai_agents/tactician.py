from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from src.ai_engine.core.errors import AgentOutputError
from src.ai_engine.services.llm_client import LLMClient
from src.ai_engine.utils.json_utils import extract_json_object
from src.ai_engine.domain.schemas import DataMinerResult, TacticalAnalysisItem, TacticalReport


import os
from pathlib import Path
PROMPT_PATH = Path(__file__).parent / "prompts" / "tactician.md"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()


class TacticianAgent:
    def __init__(self, llm_client: LLMClient, max_retries: int = 2):
        self.llm_client = llm_client
        self.max_retries = max_retries

    def run(self, mined: DataMinerResult) -> TacticalReport:
        if not mined.critical_blunders:
            return TacticalReport(analysis=())

        payload = mined.to_tactician_payload()
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
                return self._parse_report(data)
            except Exception as exc:
                last_error = exc
                if raw_response:
                    messages.append({"role": "assistant", "content": raw_response})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "JSON trên chưa đúng schema. Hãy trả lại duy nhất "
                            "một JSON object có key analysis là list object hợp lệ."
                        ),
                    }
                )
                if attempt >= self.max_retries:
                    break

        raise AgentOutputError(f"Tactician Agent failed: {last_error}")

    def _parse_report(self, data: Mapping[str, Any]) -> TacticalReport:
        raw_items = data.get("analysis")
        if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
            raise AgentOutputError("Tactician output must contain analysis list.")

        items = []
        for raw_item in raw_items:
            if not isinstance(raw_item, Mapping):
                raise AgentOutputError("Each tactical analysis item must be an object.")
            reason = str(raw_item.get("reason") or "").strip()
            if not reason:
                raise AgentOutputError("Each tactical analysis item needs reason.")
            items.append(
                TacticalAnalysisItem(
                    move_number=int(raw_item.get("move_number")),
                    side=str(raw_item.get("side") or ""),
                    move=str(raw_item.get("move") or ""),
                    reason=reason,
                    category=(
                        str(raw_item.get("category"))
                        if raw_item.get("category") is not None
                        else None
                    ),
                    severity=(
                        str(raw_item.get("severity"))
                        if raw_item.get("severity") is not None
                        else None
                    ),
                )
            )
        return TacticalReport(analysis=tuple(items))
