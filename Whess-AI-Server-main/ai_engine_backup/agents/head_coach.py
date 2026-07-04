from __future__ import annotations

import json
from typing import Any, Mapping

from src.ai_engine.errors import AgentOutputError
from src.ai_engine.llm.client import LLMClient
from src.ai_engine.llm.json_utils import extract_json_object
from src.ai_engine.schemas import DataMinerResult, TacticalReport


SYSTEM_PROMPT = """
Bạn là Head Coach Agent của một hệ thống phân tích cờ vua.
Nhiệm vụ của bạn là tổng hợp dữ liệu thống kê, khai cuộc, các lỗi chiến thuật
và ELO dự đoán thành một đoạn nhận xét tiếng Việt ngắn gọn.

Chỉ trả về JSON hợp lệ theo schema:
{
  "explanation": "Một đoạn nhận xét 3-5 câu, rõ bên Trắng/Đen, khai cuộc, lỗi chính và mức ELO nếu có."
}

Giọng văn chuyên môn, dễ hiểu, không tâng bốc quá mức, không thêm markdown.
Nếu has_critical_blunders=false hoặc tactical_analysis rỗng, hãy nói rõ ván này
không có blunder/sai lầm chiến thuật lớn theo Stockfish và không được tự bịa lỗi
khai cuộc. Khi CPL trung bình thấp, nhận xét theo hướng hai bên chơi ổn định.
""".strip()


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
