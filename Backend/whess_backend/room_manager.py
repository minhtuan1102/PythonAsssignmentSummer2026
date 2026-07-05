from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass
from typing import Any

from whess_backend.chess_engine import GameEngine, ValidatedMove
from whess_backend.clock import ClockManager
from whess_backend.config import Settings
from whess_backend.errors import BackendError, invalid_payload
from whess_backend.models import (
    ClockState,
    Color,
    FinishedGameSnapshot,
    GameOver,
    Player,
    PlayerSlots,
    Room,
    opposite_color,
)

ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MoveOutcome:
    room_id: str
    move_event: dict[str, Any] | None = None
    game_over: GameOver | None = None


@dataclass(frozen=True)
class LeaveOutcome:
    room_id: str | None
    game_over: GameOver | None = None
    deleted: bool = False


class RoomManager:
    def __init__(
        self,
        settings: Settings,
        engine: GameEngine | None = None,
        clock: ClockManager | None = None,
    ):
        self.settings = settings
        self.engine = engine or GameEngine()
        self.clock = clock or ClockManager()
        self.rooms: dict[str, Room] = {}
        self.socket_to_room: dict[str, str] = {}
        self.lock = asyncio.Lock()

    async def create_room(self, socket_id: str, time_control_minutes: object) -> Room:
        minutes = self._parse_time_control(time_control_minutes)
        async with self.lock:
            room_id = self._generate_room_code()
            now = self.clock.epoch_ms()
            room = Room(
                room_id=room_id,
                status="waiting",
                time_control=f"{minutes}+0",
                time_control_ms=minutes * 60 * 1000,
                players=PlayerSlots(white=Player(socket_id=socket_id, color="white")),
                clocks=ClockState(
                    white=minutes * 60 * 1000,
                    black=minutes * 60 * 1000,
                ),
                created_at=now,
                last_activity_at=now,
            )
            self.rooms[room_id] = room
            self.socket_to_room[socket_id] = room_id
            logger.info(
                "[ROOM %s] room_created: socketId=%s timeControl=%s",
                room_id,
                socket_id,
                room.time_control,
            )
            return room

    async def join_room(self, socket_id: str, raw_room_id: object) -> Room:
        room_id = self._normalize_room_id(raw_room_id)
        async with self.lock:
            room = self._get_room(room_id)
            if room.status == "finished":
                raise BackendError("ROOM_FINISHED")
            if room.players.black is not None and room.players.black.connected:
                raise BackendError("ROOM_FULL")
            if room.players.white is None or not room.players.white.connected:
                raise BackendError("ROOM_NOT_FOUND")

            room.players.black = Player(socket_id=socket_id, color="black")
            room.status = "playing"
            self.socket_to_room[socket_id] = room_id
            self.clock.start(room)
            logger.info(
                "[ROOM %s] room_joined: socketId=%s color=black",
                room_id,
                socket_id,
            )
            return room

    async def make_move(self, socket_id: str, payload: dict[str, Any]) -> MoveOutcome:
        room_id = self._normalize_room_id(payload.get("roomId"))
        from_square = payload.get("from")
        to_square = payload.get("to")
        promotion = payload.get("promotion")

        async with self.lock:
            room = self._get_room(room_id)
            color = self._require_player_color(room, socket_id)
            if room.status != "playing":
                raise BackendError("GAME_NOT_ACTIVE")
            if color != room.turn:
                raise BackendError("NOT_YOUR_TURN")

            validated = self.engine.validate_move(
                board=room.board,
                from_square=from_square,
                to_square=to_square,
                promotion=promotion,
            )

            clock_result = self.clock.apply_move_time(room)
            if clock_result.timeout_color is not None:
                game_over = self._finish_timeout(room, clock_result.timeout_color)
                return MoveOutcome(room_id=room.room_id, game_over=game_over)

            room.board.push(validated.move)
            room.moves_san.append(validated.san)
            game_over = self.engine.detect_game_over(room.room_id, room.board, color)

            if game_over is not None:
                self._finish_room(room, game_over.result, game_over.reason)
            else:
                self.clock.switch_turn(room, self.engine.current_turn(room.board))

            move_event = self._move_event(room, validated)
            logger.info(
                "[ROOM %s] move_made: color=%s san=%s timeSpent=%s",
                room.room_id,
                color,
                validated.san,
                room.clock_times[-1] if room.clock_times else 0,
            )
            return MoveOutcome(
                room_id=room.room_id,
                move_event=move_event,
                game_over=game_over,
            )

    async def resign(self, socket_id: str, raw_room_id: object) -> GameOver:
        room_id = self._normalize_room_id(raw_room_id)
        async with self.lock:
            room = self._get_room(room_id)
            color = self._require_player_color(room, socket_id)
            if room.status != "playing":
                raise BackendError("GAME_NOT_ACTIVE")
            result = "0-1" if color == "white" else "1-0"
            return self._finish_room(room, result, "resign")

    async def leave_room(self, socket_id: str, raw_room_id: object) -> LeaveOutcome:
        room_id = self._normalize_room_id(raw_room_id)
        async with self.lock:
            room = self._get_room(room_id)
            return self._leave_socket(room, socket_id)

    async def disconnect(self, socket_id: str) -> LeaveOutcome:
        async with self.lock:
            room_id = self.socket_to_room.get(socket_id)
            if room_id is None:
                return LeaveOutcome(room_id=None)
            room = self.rooms.get(room_id)
            if room is None:
                self.socket_to_room.pop(socket_id, None)
                return LeaveOutcome(room_id=room_id, deleted=True)
            return self._leave_socket(room, socket_id)

    async def timeout_turn(self, room_id: str, color: Color) -> GameOver | None:
        async with self.lock:
            room = self.rooms.get(room_id)
            if room is None or room.status != "playing" or room.turn != color:
                return None
            left = self.clock.active_time_left_ms(room)
            if left is None or left > 0:
                return None
            logger.info("[ROOM %s] clock_timeout: side=%s", room_id, color)
            return self._finish_timeout(room, color)

    async def get_snapshot(self, room_id: str) -> FinishedGameSnapshot | None:
        async with self.lock:
            room = self.rooms.get(room_id)
            return room.to_finished_snapshot() if room is not None else None

    async def set_analysis(self, room_id: str, payload: dict[str, Any]) -> None:
        async with self.lock:
            room = self.rooms.get(room_id)
            if room is not None:
                room.analysis = payload
                room.last_activity_at = self.clock.epoch_ms()

    async def cleanup_inactive(self) -> list[str]:
        now = self.clock.epoch_ms()
        stale_room_ids: list[str] = []
        async with self.lock:
            for room_id, room in list(self.rooms.items()):
                age = now - room.last_activity_at
                if room.status in {"waiting", "finished"} and (
                    age >= self.settings.room_inactive_cleanup_ms
                ):
                    stale_room_ids.append(room_id)
            for room_id in stale_room_ids:
                logger.info("[ROOM %s] cleanup: reason=inactive", room_id)
                self._delete_room(room_id)
        return stale_room_ids

    async def room_clocks(self, room_id: str) -> dict[str, int] | None:
        async with self.lock:
            room = self.rooms.get(room_id)
            if room is None:
                return None
            return self.clock.snapshot(room)

    async def room_state(self, room_id: str) -> dict[str, Any] | None:
        async with self.lock:
            room = self.rooms.get(room_id)
            if room is None:
                return None
            return room.public_state(clocks=self.clock.snapshot(room))

    def _parse_time_control(self, value: object) -> int:
        try:
            minutes = int(value)
        except (TypeError, ValueError) as exc:
            raise invalid_payload() from exc
        if minutes not in self.settings.allowed_time_controls:
            raise invalid_payload("Unsupported time control")
        return minutes

    def _generate_room_code(self) -> str:
        while True:
            code = "".join(
                secrets.choice(ROOM_CODE_ALPHABET)
                for _ in range(self.settings.room_code_length)
            )
            if code not in self.rooms:
                return code

    @staticmethod
    def _normalize_room_id(value: object) -> str:
        if value is None:
            raise invalid_payload()
        room_id = str(value).strip().upper()
        if not room_id:
            raise invalid_payload()
        return room_id

    def _get_room(self, room_id: str) -> Room:
        room = self.rooms.get(room_id)
        if room is None:
            raise BackendError("ROOM_NOT_FOUND")
        return room

    def _require_player_color(self, room: Room, socket_id: str) -> Color:
        color = room.players.color_for_socket(socket_id)
        if color is None:
            raise BackendError("ROOM_NOT_FOUND")
        return color

    def _move_event(self, room: Room, validated: ValidatedMove) -> dict[str, Any]:
        event: dict[str, Any] = {
            "san": validated.san,
            "from": validated.from_square,
            "to": validated.to_square,
            "fen": room.board.fen(),
            "turn": room.turn,
            "clocks": self.clock.snapshot(room),
            "moveNumber": len(room.moves_san),
        }
        if validated.promotion:
            event["promotion"] = validated.promotion
        return event

    def _finish_timeout(self, room: Room, color: Color) -> GameOver:
        result = "0-1" if color == "white" else "1-0"
        return self._finish_room(room, result, "timeout")

    def _finish_room(self, room: Room, result: str, reason: str) -> GameOver:
        room.status = "finished"
        room.result = result
        room.reason = reason  # type: ignore[assignment]
        room.last_activity_at = self.clock.epoch_ms()
        self.clock.stop(room)
        logger.info(
            "[ROOM %s] game_over: result=%s reason=%s moveCount=%s",
            room.room_id,
            result,
            reason,
            len(room.moves_san),
        )
        return GameOver(room_id=room.room_id, result=result, reason=room.reason)

    def _leave_socket(self, room: Room, socket_id: str) -> LeaveOutcome:
        color = room.players.color_for_socket(socket_id)
        if color is None:
            self.socket_to_room.pop(socket_id, None)
            return LeaveOutcome(room_id=room.room_id)

        player = room.players.get(color)
        if player is not None:
            player.connected = False
        self.socket_to_room.pop(socket_id, None)
        logger.info(
            "[ROOM %s] disconnect: color=%s status=%s",
            room.room_id,
            color,
            room.status,
        )

        if room.status == "waiting":
            room_id = room.room_id
            logger.info("[ROOM %s] cleanup: reason=waiting_player_left", room_id)
            self._delete_room(room_id)
            return LeaveOutcome(room_id=room_id, deleted=True)

        if room.status == "playing":
            result = "0-1" if color == "white" else "1-0"
            game_over = self._finish_room(room, result, "abandon")
            return LeaveOutcome(room_id=room.room_id, game_over=game_over)

        if not room.players.socket_ids():
            room_id = room.room_id
            logger.info("[ROOM %s] cleanup: reason=all_players_left", room_id)
            self._delete_room(room_id)
            return LeaveOutcome(room_id=room_id, deleted=True)

        room.last_activity_at = self.clock.epoch_ms()
        return LeaveOutcome(room_id=room.room_id)

    def _delete_room(self, room_id: str) -> None:
        room = self.rooms.pop(room_id, None)
        if room is None:
            return
        for player in (room.players.white, room.players.black):
            if player is not None:
                self.socket_to_room.pop(player.socket_id, None)
