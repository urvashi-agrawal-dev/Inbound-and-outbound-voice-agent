"""In-memory session store with optional Redis backing."""

import json
from typing import Any

import structlog

from app.config import get_settings
from app.core.conversation.manager import ConversationManager

logger = structlog.get_logger()

_sessions: dict[str, ConversationManager] = {}
_redis_client = None


async def _get_redis():
    global _redis_client
    if _redis_client is None and get_settings().use_redis:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(get_settings().redis_url)
    return _redis_client


async def get_or_create_session(call_id: str) -> ConversationManager:
    if call_id in _sessions:
        return _sessions[call_id]

    manager = ConversationManager(call_id=call_id)
    _sessions[call_id] = manager

    redis = await _get_redis()
    if redis:
        await redis.setex(
            f"session:{call_id}",
            get_settings().conversation_timeout_seconds,
            json.dumps({"call_id": call_id, "state": manager.memory.current_state.value}),
        )

    return manager


async def remove_session(call_id: str) -> ConversationManager | None:
    manager = _sessions.pop(call_id, None)
    redis = await _get_redis()
    if redis:
        await redis.delete(f"session:{call_id}")
    return manager


def get_active_session_count() -> int:
    return len(_sessions)
