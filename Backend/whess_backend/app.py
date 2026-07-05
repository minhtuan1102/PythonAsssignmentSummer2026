from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import socketio
from fastapi import FastAPI

from whess_backend.ai_client import AiClient
from whess_backend.config import Settings
from whess_backend.room_manager import RoomManager
from whess_backend.socket_gateway import SocketGateway


def create_fastapi_app(settings: Settings, gateway: SocketGateway) -> FastAPI:
    @asynccontextmanager
    async def lifespan(api: FastAPI):
        await gateway.start_background_tasks()
        try:
            yield
        finally:
            await gateway.stop_background_tasks()
            await gateway.ai_client.close()

    api = FastAPI(
        title="Whess Web Game Server",
        version="0.1.0",
        lifespan=lifespan,
    )
    api.state.settings = settings
    api.state.gateway = gateway
    api.state.manager = gateway.manager
    api.state.ai_client = gateway.ai_client

    @api.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "rooms": len(gateway.manager.rooms),
        }

    return api


def create_app(
    settings: Settings | None = None,
    manager: RoomManager | None = None,
    ai_client: AiClient | None = None,
    sio: socketio.AsyncServer | None = None,
) -> socketio.ASGIApp:
    settings = settings or Settings.from_env()
    manager = manager or RoomManager(settings=settings)
    ai_client = ai_client or AiClient(settings=settings)
    gateway = SocketGateway(
        settings=settings,
        manager=manager,
        ai_client=ai_client,
        sio=sio,
    )
    gateway.register_handlers()
    api = create_fastapi_app(settings, gateway)
    return socketio.ASGIApp(gateway.sio, other_asgi_app=api)


app = create_app()
