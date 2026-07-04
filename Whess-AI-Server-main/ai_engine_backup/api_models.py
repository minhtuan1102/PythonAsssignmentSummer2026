from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.ai_engine.schemas import AnalysisContext


class EcoPayload(BaseModel):
    code: str = "UNKNOWN"
    name: str = "Unknown Opening"


class Step3AnalysisRequest(BaseModel):
    pgn: str = Field(..., min_length=1)
    cpl_sequence: list[float]
    blunder_flags: list[bool | int] = Field(default_factory=list)
    clock_times: list[float] = Field(default_factory=list)
    result: str | None = None
    time_control: str | None = None
    white_elo: int | None = None
    black_elo: int | None = None
    eco: EcoPayload | None = None
    stockfish_records: list[dict[str, Any]] = Field(default_factory=list)
    include_debug: bool = False

    def to_context(self) -> AnalysisContext:
        dump = getattr(self, "model_dump", None)
        payload = dump() if dump else self.dict()
        payload.pop("include_debug", None)
        return AnalysisContext.from_mapping(payload)


class Step3AnalysisResponse(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class PredictEloRequest(BaseModel):
    pgn: str = Field(..., min_length=1)
    clock_times: list[float] = Field(default_factory=list)
    result: str | None = None
    time_control: str | None = None
    include_debug: bool = False


class PredictEloResponse(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
