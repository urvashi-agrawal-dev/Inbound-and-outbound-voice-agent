"""FastAPI application entry point."""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.config import get_settings
from app.services.database import engine, Base
from app.services.websocket_manager import ws_manager
from app.services.live_call_state import get_live_state
from fastapi import WebSocket, WebSocketDisconnect
import json

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("starting_karta_sdr", version=__version__, env=settings.app_env)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()
    logger.info("shutting_down_karta_sdr")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="AI Voice SDR - Inbound lead qualification, scoring, and booking",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.websocket("/ws/calls/{call_id}")
    async def websocket_call(websocket: WebSocket, call_id: str):
        await ws_manager.connect(call_id, websocket)
        live = get_live_state(call_id)
        await websocket.send_text(json.dumps({
            "event": "connected",
            "data": live.to_live_payload(),
        }))
        try:
            while True:
                msg = await websocket.receive_text()
                data = json.loads(msg)
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"event": "pong", "data": {}}))
        except WebSocketDisconnect:
            ws_manager.disconnect(call_id, websocket)

    return app


app = create_app()
