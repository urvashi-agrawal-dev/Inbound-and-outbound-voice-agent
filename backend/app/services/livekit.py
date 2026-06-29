"""LiveKit voice orchestration integration."""

import json
from typing import Any

import structlog
from livekit import api

from app.config import get_settings

logger = structlog.get_logger()


class LiveKitService:
    """Integrates with LiveKit for real-time voice agent rooms."""

    def __init__(self):
        settings = get_settings()
        self.url = settings.livekit_url
        self.api_key = settings.livekit_api_key
        self.api_secret = settings.livekit_api_secret

    def create_room_token(
        self,
        room_name: str,
        participant_identity: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        token = api.AccessToken(self.api_key, self.api_secret)
        token.with_identity(participant_identity)
        token.with_name(participant_identity)
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
        if metadata:
            token.with_metadata(json.dumps(metadata))
        return token.to_jwt()

    async def create_room(self, room_name: str) -> dict[str, Any]:
        lkapi = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        try:
            room = await lkapi.room.create_room(
                api.CreateRoomRequest(name=room_name)
            )
            return {"room_name": room.name, "sid": room.sid}
        finally:
            await lkapi.aclose()

    async def delete_room(self, room_name: str) -> None:
        lkapi = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        try:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
        finally:
            await lkapi.aclose()

    def get_connection_info(self, call_id: str) -> dict[str, str]:
        room_name = f"karta-call-{call_id}"
        agent_token = self.create_room_token(room_name, f"agent-{call_id}")
        caller_token = self.create_room_token(room_name, f"caller-{call_id}")
        return {
            "url": self.url,
            "room_name": room_name,
            "agent_token": agent_token,
            "caller_token": caller_token,
        }
