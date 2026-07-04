from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class EcoInfo:
    code: str
    name: str

    @classmethod
    def unknown(cls) -> "EcoInfo":
        return cls(code="UNKNOWN", name="Unknown Opening")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "EcoInfo":
        if not value:
            return cls.unknown()
        return cls(
            code=str(value.get("code") or "UNKNOWN"),
            name=str(value.get("name") or "Unknown Opening"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "name": self.name}


@dataclass(frozen=True)
class GameStats:
    white_avg_cpl: float
    black_avg_cpl: float
    white_blunders: int
    black_blunders: int
    total_moves: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "white_avg_cpl": self.white_avg_cpl,
            "black_avg_cpl": self.black_avg_cpl,
            "white_blunders": self.white_blunders,
            "black_blunders": self.black_blunders,
            "total_moves": self.total_moves,
        }


@dataclass(frozen=True)
class MoveMetric:
    ply: int
    move_number: int
    side: str
    move: str
    cpl: float
    is_blunder: bool
    time_spent: float | None = None
    fen_before: str | None = None
    fen_after: str | None = None
    best_move: str | None = None
    eval_before_cp: float | None = None
    eval_after_cp: float | None = None

    def to_dict(self, include_board: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ply": self.ply,
            "move_number": self.move_number,
            "side": self.side,
            "move": self.move,
            "cpl": self.cpl,
            "is_blunder": self.is_blunder,
            "time_spent": self.time_spent,
        }
        if include_board:
            data.update(
                {
                    "fen_before": self.fen_before,
                    "fen_after": self.fen_after,
                    "best_move": self.best_move,
                    "eval_before_cp": self.eval_before_cp,
                    "eval_after_cp": self.eval_after_cp,
                }
            )
        return {key: value for key, value in data.items() if value is not None}


@dataclass(frozen=True)
class TacticalAnalysisItem:
    move_number: int
    side: str
    move: str
    reason: str
    category: str | None = None
    severity: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "move_number": self.move_number,
            "side": self.side,
            "move": self.move,
            "reason": self.reason,
        }
        if self.category:
            data["category"] = self.category
        if self.severity:
            data["severity"] = self.severity
        return data


@dataclass(frozen=True)
class TacticalReport:
    analysis: tuple[TacticalAnalysisItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"analysis": [item.to_dict() for item in self.analysis]}


@dataclass(frozen=True)
class AnalysisContext:
    pgn: str
    cpl_sequence: Sequence[float]
    blunder_flags: Sequence[bool | int] = field(default_factory=tuple)
    clock_times: Sequence[float] = field(default_factory=tuple)
    result: str | None = None
    time_control: str | None = None
    white_elo: int | None = None
    black_elo: int | None = None
    eco: EcoInfo | None = None
    stockfish_records: Sequence[Mapping[str, Any]] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AnalysisContext":
        return cls(
            pgn=str(value.get("pgn") or ""),
            cpl_sequence=tuple(float(item) for item in value.get("cpl_sequence", ())),
            blunder_flags=tuple(value.get("blunder_flags", ())),
            clock_times=tuple(float(item) for item in value.get("clock_times", ())),
            result=value.get("result"),
            time_control=value.get("time_control"),
            white_elo=value.get("white_elo"),
            black_elo=value.get("black_elo"),
            eco=EcoInfo.from_mapping(value.get("eco")) if value.get("eco") else None,
            stockfish_records=tuple(value.get("stockfish_records", ())),
        )

    def elo_dict(self) -> dict[str, int | None]:
        return {"white": self.white_elo, "black": self.black_elo}


@dataclass(frozen=True)
class DataMinerResult:
    eco: EcoInfo
    stats: GameStats
    critical_blunders: tuple[MoveMetric, ...]
    move_metrics: tuple[MoveMetric, ...]
    result: str | None = None
    time_control: str | None = None
    white_elo: int | None = None
    black_elo: int | None = None

    def to_tactician_payload(self) -> dict[str, Any]:
        return {
            "eco": self.eco.to_dict(),
            "stats": self.stats.to_dict(),
            "analysis_policy": {
                "critical_blunders_contains_only_major_candidates": True,
                "do_not_invent_errors_when_list_is_empty": True,
            },
            "critical_blunders": [
                move.to_dict(include_board=True) for move in self.critical_blunders
            ],
            "result": self.result,
            "time_control": self.time_control,
        }

    def to_coach_payload(self, tactical_report: TacticalReport) -> dict[str, Any]:
        return {
            "eco": self.eco.to_dict(),
            "stats": self.stats.to_dict(),
            "has_critical_blunders": bool(self.critical_blunders),
            "critical_blunders": [
                move.to_dict(include_board=False) for move in self.critical_blunders
            ],
            "tactical_analysis": tactical_report.to_dict()["analysis"],
            "predicted_elo": {"white": self.white_elo, "black": self.black_elo},
            "result": self.result,
            "time_control": self.time_control,
        }


@dataclass(frozen=True)
class MultiAgentReport:
    eco: EcoInfo
    stats: GameStats
    explanation: str
    critical_blunders: tuple[MoveMetric, ...]
    tactical_report: TacticalReport
    white_elo: int | None = None
    black_elo: int | None = None

    def to_api_data(self, include_debug: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "eco": self.eco.to_dict(),
            "stats": self.stats.to_dict(),
            "explanation": self.explanation,
        }
        if self.white_elo is not None:
            data["white_elo"] = self.white_elo
        if self.black_elo is not None:
            data["black_elo"] = self.black_elo
        if include_debug:
            data["critical_blunders"] = [
                move.to_dict(include_board=True) for move in self.critical_blunders
            ]
            data["tactical_report"] = self.tactical_report.to_dict()
        return data
