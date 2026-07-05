from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from whess_backend.chess_engine import moves_to_movetext
from whess_backend.config import Settings
from whess_backend.models import FinishedGameSnapshot

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AiResult:
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None

    def to_socket_payload(self, basic_result: dict[str, str]) -> dict[str, Any]:
        if self.success:
            return {
                "success": True,
                "data": self.data,
                "basicResult": basic_result,
                "error": None,
            }
        return {
            "success": False,
            "basicResult": basic_result,
            "error": self.error or "Không thể phân tích bằng AI.",
        }


class AiClient:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ):
        self.settings = settings
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=settings.ai_engine_timeout_seconds
        )

    def build_payload(self, snapshot: FinishedGameSnapshot) -> dict[str, Any]:
        return {
            "pgn": moves_to_movetext(snapshot.moves_san),
            "clock_times": list(snapshot.clock_times),
            "result": snapshot.result,
            "time_control": snapshot.time_control,
            "include_debug": self.settings.ai_engine_include_debug,
        }

    async def analyze_snapshot(self, snapshot: FinishedGameSnapshot) -> AiResult:
        if not snapshot.moves_san:
            return AiResult(
                success=False,
                error="Không có nước đi nào để phân tích.",
            )
        if len(snapshot.moves_san) != len(snapshot.clock_times):
            return AiResult(
                success=False,
                error="Dữ liệu thời gian và nước đi không khớp.",
            )

        payload = self.build_payload(snapshot)
        started = time.monotonic()
        logger.info(
            "[ROOM %s] ai_request: pgnLength=%s clockTimesLength=%s include_debug=%s",
            snapshot.room_id,
            len(payload["pgn"]),
            len(payload["clock_times"]),
            payload["include_debug"],
        )
        try:
            response = await self.client.post(self.settings.ai_engine_url, json=payload)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.info(
                "[ROOM %s] ai_response: success=false durationMs=%s error=%s",
                snapshot.room_id,
                int((time.monotonic() - started) * 1000),
                exc,
            )
            return AiResult(
                success=False,
                error=f"Không thể phân tích bằng AI lúc này: {exc}",
            )

        if not body.get("success"):
            logger.info(
                "[ROOM %s] ai_response: success=false durationMs=%s error=%s",
                snapshot.room_id,
                int((time.monotonic() - started) * 1000),
                body.get("error"),
            )
            return AiResult(
                success=False,
                error=str(body.get("error") or "AI service returned an error."),
            )
        data = body.get("data")
        if not isinstance(data, dict):
            logger.info(
                "[ROOM %s] ai_response: success=false durationMs=%s error=invalid_data",
                snapshot.room_id,
                int((time.monotonic() - started) * 1000),
            )
            return AiResult(success=False, error="AI service response is invalid.")
        logger.info(
            "[ROOM %s] ai_response: success=true durationMs=%s",
            snapshot.room_id,
            int((time.monotonic() - started) * 1000),
        )
        return AiResult(success=True, data=data)

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()
