from __future__ import annotations

import time
from dataclasses import dataclass

from whess_backend.models import Color, Room


@dataclass(frozen=True)
class MoveClockResult:
    elapsed_seconds: float
    timeout_color: Color | None = None


class ClockManager:
    def epoch_ms(self) -> int:
        return int(time.time() * 1000)

    def monotonic_ms(self) -> int:
        return int(time.monotonic() * 1000)

    def start(self, room: Room) -> None:
        now_epoch = self.epoch_ms()
        room.turn = "white"
        room.turn_started_at = now_epoch
        room.turn_started_monotonic_ms = self.monotonic_ms()
        room.last_activity_at = now_epoch

    def snapshot(self, room: Room) -> dict[str, int]:
        clocks = room.clocks.to_dict()
        if room.status != "playing" or room.turn_started_monotonic_ms is None:
            return clocks
        elapsed = max(0, self.monotonic_ms() - room.turn_started_monotonic_ms)
        clocks[room.turn] = max(0, clocks[room.turn] - elapsed)
        return clocks

    def apply_move_time(self, room: Room) -> MoveClockResult:
        if room.turn_started_monotonic_ms is None:
            return MoveClockResult(elapsed_seconds=0.0)

        now_mono = self.monotonic_ms()
        elapsed_ms = max(0, now_mono - room.turn_started_monotonic_ms)
        mover = room.turn
        remaining = room.clocks.get(mover)

        if elapsed_ms >= remaining:
            room.clocks.set(mover, 0)
            room.turn_started_at = None
            room.turn_started_monotonic_ms = None
            return MoveClockResult(
                elapsed_seconds=round(remaining / 1000, 2),
                timeout_color=mover,
            )

        room.clocks.set(mover, remaining - elapsed_ms)
        elapsed_seconds = round(elapsed_ms / 1000, 2)
        room.clock_times.append(elapsed_seconds)
        return MoveClockResult(elapsed_seconds=elapsed_seconds)

    def switch_turn(self, room: Room, next_turn: Color) -> None:
        now_epoch = self.epoch_ms()
        room.turn = next_turn
        room.turn_started_at = now_epoch
        room.turn_started_monotonic_ms = self.monotonic_ms()
        room.last_activity_at = now_epoch

    def stop(self, room: Room) -> None:
        room.turn_started_at = None
        room.turn_started_monotonic_ms = None

    def active_time_left_ms(self, room: Room) -> int | None:
        if room.status != "playing":
            return None
        return self.snapshot(room).get(room.turn)
