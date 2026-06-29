"""Unified voice orchestration abstraction over Vapi and LiveKit."""

from typing import Any, Protocol

import structlog

from app.config import get_settings
from app.services.livekit import LiveKitService
from app.services.vapi import VapiService

logger = structlog.get_logger()


class VoiceOrchestrator:
    """Routes voice operations to the configured provider (Vapi or LiveKit)."""

    def __init__(self):
        settings = get_settings()
        self.provider = settings.voice_provider
        self._vapi = VapiService()
        self._livekit = LiveKitService()

    async def initiate_call(
        self,
        phone_number: str | None = None,
        call_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.provider == "vapi":
            if not phone_number:
                raise ValueError("phone_number required for Vapi outbound calls")
            result = await self._vapi.create_outbound_call(phone_number, metadata)
            return {
                "provider": "vapi",
                "external_call_id": result.get("id"),
                "status": result.get("status", "queued"),
                "raw": result,
            }

        if not call_id:
            raise ValueError("call_id required for LiveKit rooms")
        room = await self._livekit.create_room(f"karta-call-{call_id}")
        connection = self._livekit.get_connection_info(call_id)
        return {
            "provider": "livekit",
            "room_name": room["room_name"],
            "connection": connection,
            "status": "ready",
        }

    async def end_call(self, external_id: str) -> dict[str, Any]:
        if self.provider == "vapi":
            return await self._vapi.end_call(external_id)
        await self._livekit.delete_room(external_id)
        return {"status": "ended"}

    async def get_call_status(self, external_id: str) -> dict[str, Any]:
        if self.provider == "vapi":
            return await self._vapi.get_call(external_id)
        return {"provider": "livekit", "room_name": external_id, "status": "active"}

    def get_webhook_handler(self) -> str:
        return f"/api/v1/webhooks/{self.provider}"
