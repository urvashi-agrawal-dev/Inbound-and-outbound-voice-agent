"""Vapi voice orchestration integration."""

from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()

VAPI_BASE_URL = "https://api.vapi.ai"


class VapiService:
    """Integrates with Vapi for outbound/inbound voice call orchestration."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.vapi_api_key
        self.assistant_id = settings.vapi_assistant_id
        self.phone_number_id = settings.vapi_phone_number_id
        self.webhook_secret = settings.vapi_webhook_secret

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_outbound_call(
        self,
        phone_number: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "assistantId": self.assistant_id,
            "phoneNumberId": self.phone_number_id,
            "customer": {"number": phone_number},
            "metadata": metadata or {},
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{VAPI_BASE_URL}/call/phone",
                headers=self._headers(),
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_call(self, call_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{VAPI_BASE_URL}/call/{call_id}",
                headers=self._headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    async def end_call(self, call_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{VAPI_BASE_URL}/call/{call_id}/end",
                headers=self._headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            return response.json()

    def build_assistant_config(self, server_url: str) -> dict[str, Any]:
        """Configuration for Vapi assistant pointing to our webhook server."""
        return {
            "name": "Karta SDR Agent",
            "model": {
                "provider": "custom-llm",
                "url": f"{server_url}/api/v1/webhooks/vapi/llm",
            },
            "voice": {
                "provider": "custom-voice",
                "url": f"{server_url}/api/v1/webhooks/vapi/tts",
            },
            "transcriber": {
                "provider": "custom-transcriber",
                "url": f"{server_url}/api/v1/webhooks/vapi/stt",
            },
            "firstMessage": (
                "Hi there! This is Alex from Karta SDR. "
                "Thanks for your interest in our AI voice platform. "
                "May I ask who I'm speaking with?"
            ),
            "endCallFunctionEnabled": True,
            "recordingEnabled": True,
            "interruptionsEnabled": True,
            "serverUrl": f"{server_url}/api/v1/webhooks/vapi/events",
        }

    def verify_webhook(self, signature: str | None) -> bool:
        if not self.webhook_secret:
            return True
        return signature == self.webhook_secret
