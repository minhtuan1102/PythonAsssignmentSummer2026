from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import chess

Color = Literal["white", "black"]
RoomStatus = Literal["waiting", "playing", "finished"]
GameReason = Literal[
    "checkmate",
    "timeout",
    "resign",
    "abandon",
    "stalemate",
    "threefold",
    "insufficient_material",
]


def opposite_color(color: Color) -> Color:
    return "black" if color == "white" else "white"


def chess_turn_to_color(turn: chess.Color) -> Color:
    return "white" if turn == chess.WHITE else "black"


@dataclass
class Player:
    socket_id: str
    color: Color
    connected: bool = True


@dataclass
class PlayerSlots:
    white: Player | None = None
    black: Player | None = None

    def get(self, color: Color) -> Player | None:
        return self.white if color == "white" else self.black

    def set(self, color: Color, player: Player | None) -> None:
        if color == "white":
            self.white = player
        else:
            self.black = player

    def color_for_socket(self, socket_id: str) -> Color | None:
        if self.white and self.white.socket_id == socket_id:
            return "white"
        if self.black and self.black.socket_id == socket_id:
            return "black"
        return None

    def socket_ids(self) -> list[str]:
        return [
            player.socket_id
            for player in (self.white, self.black)
            if player is not None and player.connected
        ]


@dataclass
class ClockState:
    white: int
    black: int

    def get(self, color: Color) -> int:
        return self.white if color == "white" else self.black

    def set(self, color: Color, value_ms: int) -> None:
        value_ms = max(0, int(value_ms))
        if color == "white":
            self.white = value_ms
        else:
            self.black = value_ms

    def to_dict(self) -> dict[str, int]:
        return {"white": self.white, "black": self.black}


@dataclass(frozen=True)
class GameOver:
    room_id: str
    result: str
    reason: GameReason

    def basic_result(self) -> dict[str, str]:
        return {"result": self.result, "reason": self.reason}


@dataclass(frozen=True)
class FinishedGameSnapshot:
    room_id: str
    moves_san: tuple[str, ...]
    clock_times: tuple[float, ...]
    result: str
    reason: GameReason
    time_control: str

    def basic_result(self) -> dict[str, str]:
        return {"result": self.result, "reason": self.reason}


@dataclass
class Room:
    room_id: str
    status: RoomStatus
    time_control: str
    time_control_ms: int
    players: PlayerSlots
    board: chess.Board = field(default_factory=chess.Board)
    moves_san: list[str] = field(default_factory=list)
    clock_times: list[float] = field(default_factory=list)
    clocks: ClockState = field(default_factory=lambda: ClockState(0, 0))
    turn: Color = "white"
    turn_started_at: int | None = None
    turn_started_monotonic_ms: int | None = None
    result: str | None = None
    reason: GameReason | None = None
    created_at: int = 0
    last_activity_at: int = 0
    analysis: dict[str, Any] | None = None

    def public_state(self, clocks: dict[str, int] | None = None) -> dict[str, Any]:
        state: dict[str, Any] = {
            "status": self.status,
            "fen": self.board.fen(),
            "turn": self.turn,
            "clocks": clocks or self.clocks.to_dict(),
            "moves": list(self.moves_san),
            "result": self.result,
            "reason": self.reason,
        }
        if self.analysis is not None:
            state["analysis"] = self.analysis
        return state

    def to_finished_snapshot(self) -> FinishedGameSnapshot | None:
        if self.status != "finished" or self.result is None or self.reason is None:
            return None
        return FinishedGameSnapshot(
            room_id=self.room_id,
            moves_san=tuple(self.moves_san),
            clock_times=tuple(self.clock_times),
            result=self.result,
            reason=self.reason,
            time_control=self.time_control,
        )
