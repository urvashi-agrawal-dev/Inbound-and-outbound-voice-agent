"""WebSocket connection manager for live call broadcasts."""

import json
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections per call_id."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, call_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(call_id, []).append(websocket)
        logger.info("ws_connected", call_id=call_id, clients=len(self._connections[call_id]))

    def disconnect(self, call_id: str, websocket: WebSocket) -> None:
        if call_id in self._connections:
            self._connections[call_id] = [
                ws for ws in self._connections[call_id] if ws != websocket
            ]
            if not self._connections[call_id]:
                del self._connections[call_id]
        logger.info("ws_disconnected", call_id=call_id)

    async def broadcast(self, call_id: str, event: str, data: dict[str, Any]) -> None:
        message = json.dumps({"event": event, "data": data})
        dead: list[WebSocket] = []
        for ws in self._connections.get(call_id, []):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(call_id, ws)

    def client_count(self, call_id: str) -> int:
        return len(self._connections.get(call_id, []))


ws_manager = ConnectionManager()
