"""Vapi live integration endpoints and WebSocket."""

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.scoring.lead_scorer import LeadScorer
from app.models.call import CallRecord
from app.schemas.vapi_live import (
    VapiEventRequest,
    VapiTranscriptRequest,
    VapiTranscriptResponse,
)
from app.services.database import get_db
from app.services.live_call_state import get_live_state
from app.services.session_store import get_or_create_session
from app.services.websocket_manager import ws_manager

logger = structlog.get_logger()
router = APIRouter(tags=["vapi-live"])


async def _broadcast_live(call_id: str, event: str = "live_update") -> None:
    live = get_live_state(call_id)
    await ws_manager.broadcast(call_id, event, live.to_live_payload())


def _build_scoring(manager) -> dict:
    result = LeadScorer().score(manager.memory.lead_data)
    return {
        "total_score": result.total_score,
        "tier": result.tier.value,
        "breakdown": result.breakdown,
        "qualified_for_booking": result.qualified_for_booking,
    }


@router.post("/vapi/transcript", response_model=VapiTranscriptResponse)
async def vapi_transcript(
    request: VapiTranscriptRequest,
    db: AsyncSession = Depends(get_db),
):
    live = get_live_state(request.call_id)
    live.add_transcript(request.role, request.text)

    if request.role == "assistant":
        await _broadcast_live(request.call_id, "transcript")
        scoring = _build_scoring(await get_or_create_session(request.call_id))
        return VapiTranscriptResponse(
            status="logged",
            state=live.current_state,
            score=scoring["total_score"],
            qualified=scoring["qualified_for_booking"],
            tier=scoring["tier"],
        )

    manager = await get_or_create_session(request.call_id)
    result = await manager.process_utterance(
        user_text=request.text,
        interrupted=request.interrupted,
    )

    live.update_from_utterance(result, role="user")

    # In Vapi mode the assistant speaks via Vapi — do not inject FSM text into transcript
    if not request.vapi_mode:
        live.add_transcript("assistant", result["response_text"], result["state"])

    scoring = result.get("scoring") or _build_scoring(manager)
    live.scoring = scoring

    try:
        call_uuid = uuid.UUID(request.call_id)
        stmt = select(CallRecord).where(CallRecord.id == call_uuid)
        db_result = await db.execute(stmt)
        call_record = db_result.scalar_one_or_none()
        if call_record:
            call_record.current_state = result["state"]
            call_record.lead_data = result["lead_data"]
            call_record.status = "active"
            call_record.scoring = scoring
            call_record.qualified = scoring.get("qualified_for_booking", False)
    except ValueError:
        pass

    payload = live.to_live_payload()
    payload["last_utterance"] = {
        "latency_ms": result["latency_ms"],
        "should_end": result.get("should_end", False),
        "should_book": result.get("should_book", False),
    }
    await ws_manager.broadcast(request.call_id, "utterance_processed", payload)

    return VapiTranscriptResponse(
        status="processed",
        state=result["state"],
        score=scoring["total_score"],
        qualified=scoring.get("qualified_for_booking", False),
        tier=scoring.get("tier"),
        latency_ms=result["latency_ms"],
        lead_data=result["lead_data"],
        qualification_checklist=live.qualification_checklist(),
    )


@router.post("/vapi/events")
async def vapi_events(request: VapiEventRequest):
    live = get_live_state(request.call_id)
    event_type = request.event_type
    payload = request.payload

    if event_type == "call-start":
        live.connection_status = "connected"
        live.status = "active"
    elif event_type == "call-end":
        live.connection_status = "disconnected"
        live.status = "ending"
        live.speaking_role = None
    elif event_type == "speech-start":
        live.speaking_role = payload.get("role", "assistant")
    elif event_type == "speech-end":
        live.speaking_role = None
    elif event_type == "transcript":
        role = payload.get("role", "assistant")
        text = payload.get("text", "")
        if text:
            live.add_transcript(role, text)
    elif event_type == "error":
        live.connection_status = "error"
    elif event_type == "connecting":
        live.connection_status = "connecting"

    await ws_manager.broadcast(request.call_id, event_type, live.to_live_payload())
    return {"status": "acknowledged", "event": event_type}
