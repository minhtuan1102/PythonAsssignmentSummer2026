from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is declared for runtime.
    load_dotenv = None


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    port: int = 3000
    ai_engine_url: str = "http://localhost:8000/api/predict-elo"
    ai_engine_timeout_ms: int = 60000
    ai_engine_include_debug: bool = True
    room_code_length: int = 6
    room_inactive_cleanup_ms: int = 1800000
    clock_update_interval_ms: int = 1000
    allowed_time_controls: tuple[int, ...] = (3, 5, 10, 15)

    @classmethod
    def from_env(cls, load_env_file: bool = True) -> "Settings":
        if load_env_file and load_dotenv is not None:
            load_dotenv()
        return cls(
            port=int(os.getenv("PORT", "3000")),
            ai_engine_url=os.getenv(
                "AI_ENGINE_URL", "http://localhost:8000/api/predict-elo"
            ),
            ai_engine_timeout_ms=int(os.getenv("AI_ENGINE_TIMEOUT_MS", "60000")),
            ai_engine_include_debug=_as_bool(
                os.getenv("AI_ENGINE_INCLUDE_DEBUG"), True
            ),
            room_code_length=int(os.getenv("ROOM_CODE_LENGTH", "6")),
            room_inactive_cleanup_ms=int(
                os.getenv("ROOM_INACTIVE_CLEANUP_MS", "1800000")
            ),
            clock_update_interval_ms=int(
                os.getenv("CLOCK_UPDATE_INTERVAL_MS", "1000")
            ),
        )

    @property
    def ai_engine_timeout_seconds(self) -> float:
        return self.ai_engine_timeout_ms / 1000

    @property
    def room_inactive_cleanup_seconds(self) -> float:
        return self.room_inactive_cleanup_ms / 1000

    @property
    def clock_update_interval_seconds(self) -> float:
        return self.clock_update_interval_ms / 1000
