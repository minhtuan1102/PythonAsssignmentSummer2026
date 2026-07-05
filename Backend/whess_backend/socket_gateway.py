from __future__ import annotations

import asyncio
import logging
from typing import Any

import socketio

from whess_backend.ai_client import AiClient, AiResult
from whess_backend.config import Settings
from whess_backend.errors import BackendError
from whess_backend.models import GameOver
from whess_backend.room_manager import MoveOutcome, RoomManager

logger = logging.getLogger(__name__)


class SocketGateway:
    def __init__(
        self,
        settings: Settings,
        manager: RoomManager,
        ai_client: AiClient,
        sio: socketio.AsyncServer | None = None,
    ):
        self.settings = settings
        self.manager = manager
        self.ai_client = ai_client
        self.sio = sio or socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False,
        )
        self.timeout_tasks: dict[str, asyncio.Task[None]] = {}
        self.clock_tasks: dict[str, asyncio.Task[None]] = {}
        self.analysis_tasks: set[asyncio.Task[None]] = set()
        self.cleanup_task: asyncio.Task[None] | None = None
        self._registered = False

    def register_handlers(self) -> None:
        if self._registered:
            return
        self._registered = True

        @self.sio.event
        async def connect(sid: str, environ: dict[str, Any], auth: Any) -> None:
            return None

        @self.sio.event
        async def disconnect(sid: str) -> None:
            outcome = await self.manager.disconnect(sid)
            if outcome.game_over is not None:
                await self._handle_game_over(outcome.game_over)
            if outcome.room_id:
                self._cancel_room_tasks(outcome.room_id)

        @self.sio.event
        async def create_room(sid: str, payload: dict[str, Any] | None) -> None:
            try:
                room = await self.manager.create_room(
                    sid, (payload or {}).get("timeControlMinutes")
                )
                await self.sio.enter_room(sid, room.room_id)
                await self.sio.emit(
                    "room_created",
                    {"roomId": room.room_id, "color": "white"},
                    to=sid,
                )
            except BackendError as exc:
                logger.info("room_error: socketId=%s code=%s", sid, exc.code)
                await self.sio.emit("room_error", exc.to_payload(), to=sid)

        @self.sio.event
        async def join_room(sid: str, payload: dict[str, Any] | None) -> None:
            try:
                room = await self.manager.join_room(sid, (payload or {}).get("roomId"))
                await self.sio.enter_room(sid, room.room_id)
                await self.sio.emit(
                    "room_joined",
                    {
                        "roomId": room.room_id,
                        "color": "black",
                        "state": room.public_state(
                            clocks=self.manager.clock.snapshot(room)
                        ),
                    },
                    to=sid,
                )
                await self.sio.emit("opponent_joined", {}, room=room.room_id, skip_sid=sid)
                await self.sio.emit(
                    "game_started",
                    {
                        "fen": room.board.fen(),
                        "turn": room.turn,
                        "clocks": self.manager.clock.snapshot(room),
                        "moves": list(room.moves_san),
                    },
                    room=room.room_id,
                )
                self._schedule_room_tasks(room.room_id)
            except BackendError as exc:
                logger.info("room_error: socketId=%s code=%s", sid, exc.code)
                await self.sio.emit("room_error", exc.to_payload(), to=sid)

        @self.sio.event
        async def make_move(sid: str, payload: dict[str, Any] | None) -> None:
            try:
                outcome = await self.manager.make_move(sid, payload or {})
                await self._handle_move_outcome(outcome)
            except BackendError as exc:
                logger.info("move_rejected: socketId=%s code=%s", sid, exc.code)
                await self.sio.emit(
                    "move_rejected",
                    {"reason": exc.message, "code": exc.code},
                    to=sid,
                )

        @self.sio.event
        async def resign(sid: str, payload: dict[str, Any] | None) -> None:
            try:
                game_over = await self.manager.resign(sid, (payload or {}).get("roomId"))
                await self._handle_game_over(game_over)
            except BackendError as exc:
                logger.info("room_error: socketId=%s code=%s", sid, exc.code)
                await self.sio.emit("room_error", exc.to_payload(), to=sid)

        @self.sio.event
        async def leave_room(sid: str, payload: dict[str, Any] | None) -> None:
            try:
                outcome = await self.manager.leave_room(
                    sid, (payload or {}).get("roomId")
                )
                if outcome.game_over is not None:
                    await self._handle_game_over(outcome.game_over)
                if outcome.room_id:
                    self._cancel_room_tasks(outcome.room_id)
                    await self.sio.leave_room(sid, outcome.room_id)
            except BackendError as exc:
                logger.info("room_error: socketId=%s code=%s", sid, exc.code)
                await self.sio.emit("room_error", exc.to_payload(), to=sid)

    async def start_background_tasks(self) -> None:
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_background_tasks(self) -> None:
        for room_id in list(self.timeout_tasks):
            self._cancel_room_tasks(room_id)
        if self.cleanup_task is not None:
            self.cleanup_task.cancel()
            await asyncio.gather(self.cleanup_task, return_exceptions=True)
            self.cleanup_task = None
        if self.analysis_tasks:
            await asyncio.gather(*self.analysis_tasks, return_exceptions=True)

    async def _handle_move_outcome(self, outcome: MoveOutcome) -> None:
        if outcome.move_event is not None:
            await self.sio.emit("move_made", outcome.move_event, room=outcome.room_id)
        if outcome.game_over is not None:
            await self._handle_game_over(outcome.game_over)
        else:
            self._schedule_room_tasks(outcome.room_id)

    async def _handle_game_over(self, game_over: GameOver) -> None:
        self._cancel_room_tasks(game_over.room_id)
        await self.sio.emit("game_over", game_over.basic_result(), room=game_over.room_id)
        task = asyncio.create_task(self._emit_analysis_result(game_over))
        self.analysis_tasks.add(task)
        task.add_done_callback(self.analysis_tasks.discard)

    async def _emit_analysis_result(self, game_over: GameOver) -> None:
        snapshot = await self.manager.get_snapshot(game_over.room_id)
        if snapshot is None:
            result = AiResult(
                success=False,
                error="Khong the lay du lieu van dau de phan tich.",
            )
            payload = result.to_socket_payload(game_over.basic_result())
            await self.sio.emit("analysis_result", payload, room=game_over.room_id)
            return

        result = await self.ai_client.analyze_snapshot(snapshot)
        payload = result.to_socket_payload(snapshot.basic_result())
        await self.manager.set_analysis(game_over.room_id, payload)
        await self.sio.emit("analysis_result", payload, room=game_over.room_id)

    def _schedule_room_tasks(self, room_id: str) -> None:
        self._cancel_room_tasks(room_id)
        self.timeout_tasks[room_id] = asyncio.create_task(self._timeout_loop(room_id))
        self.clock_tasks[room_id] = asyncio.create_task(self._clock_update_loop(room_id))

    def _cancel_room_tasks(self, room_id: str) -> None:
        for task_map in (self.timeout_tasks, self.clock_tasks):
            task = task_map.pop(room_id, None)
            if task is not None:
                task.cancel()

    async def _timeout_loop(self, room_id: str) -> None:
        try:
            while True:
                state = await self.manager.room_state(room_id)
                if state is None or state["status"] != "playing":
                    return
                turn = state["turn"]
                time_left = state["clocks"][turn]
                await asyncio.sleep(max(time_left / 1000, 0.01))
                game_over = await self.manager.timeout_turn(room_id, turn)
                if game_over is not None:
                    await self._handle_game_over(game_over)
                    return
        except asyncio.CancelledError:
            return

    async def _clock_update_loop(self, room_id: str) -> None:
        try:
            while True:
                await asyncio.sleep(self.settings.clock_update_interval_seconds)
                state = await self.manager.room_state(room_id)
                if state is None or state["status"] != "playing":
                    return
                await self.sio.emit(
                    "clock_update",
                    {
                        "clocks": state["clocks"],
                        "turn": state["turn"],
                        "serverTime": self.manager.clock.epoch_ms(),
                    },
                    room=room_id,
                )
        except asyncio.CancelledError:
            return

    async def _cleanup_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.settings.room_inactive_cleanup_seconds)
                stale_room_ids = await self.manager.cleanup_inactive()
                for room_id in stale_room_ids:
                    self._cancel_room_tasks(room_id)
        except asyncio.CancelledError:
            return
