"""Webhook endpoints for Vapi and LiveKit voice providers."""

import uuid

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.call import TTSRequest, STTRequest, BookingRequest
from app.services.database import get_db
from app.services.edge_tts import EdgeTTSService
from app.services.google_calendar import GoogleCalendarService
from app.services.session_store import get_or_create_session
from app.services.vapi import VapiService
from app.services.whisper import WhisperService
from app.api.routes.calls import process_utterance, end_call
from app.schemas.call import UtteranceRequest, CallEndRequest

logger = structlog.get_logger()
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/vapi/events")
async def vapi_events(
    request: Request,
    x_vapi_secret: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    vapi = VapiService()
    if not vapi.verify_webhook(x_vapi_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    event_type = payload.get("message", {}).get("type", "")
    call_data = payload.get("call", {})
    call_id = call_data.get("metadata", {}).get("call_id") or call_data.get("id", "")

    logger.info("vapi_event", event_type=event_type, call_id=call_id)

    if event_type == "transcript":
        transcript = payload.get("message", {}).get("transcript", "")
        role = payload.get("message", {}).get("role", "")
        if role == "user" and transcript:
            utterance = UtteranceRequest(text=transcript)
            return await process_utterance(call_id, utterance, db)

    if event_type in ("end-of-call-report", "hang"):
        return await end_call(call_id, CallEndRequest(reason=event_type), db)

    return {"status": "acknowledged"}


@router.post("/vapi/tts")
async def vapi_tts(request: TTSRequest):
    tts = EdgeTTSService()
    result = await tts.synthesize(request.text)
    return Response(content=result["audio"], media_type="audio/mpeg")


@router.post("/vapi/stt")
async def vapi_stt(request: STTRequest):
    if not request.audio_url:
        raise HTTPException(status_code=400, detail="audio_url required")
    whisper = WhisperService()
    result = await whisper.transcribe_url(request.audio_url)
    return {"text": result["text"], "latency_ms": result["latency_ms"]}


@router.post("/vapi/llm")
async def vapi_llm(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    messages = payload.get("messages", [])
    call_id = payload.get("call", {}).get("metadata", {}).get("call_id", str(uuid.uuid4()))

    user_text = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_text = msg.get("content", "")
            break

    utterance = UtteranceRequest(text=user_text)
    result = await process_utterance(call_id, utterance, db)
    return {"messages": [{"role": "assistant", "content": result.response_text}]}


@router.post("/livekit/events")
async def livekit_events(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    event = payload.get("event", "")
    room = payload.get("room", {}).get("name", "")
    call_id = room.replace("karta-call-", "") if room.startswith("karta-call-") else room

    logger.info("livekit_event", event=event, call_id=call_id)

    if event == "room_finished":
        return await end_call(call_id, CallEndRequest(reason="room_finished"), db)

    return {"status": "acknowledged"}


@router.post("/booking")
async def book_demo(request: BookingRequest):
    calendar = GoogleCalendarService()
    result = await calendar.book_meeting(
        attendee_email=request.attendee_email,
        attendee_name=request.attendee_name,
        company_name=request.company_name,
        preferred_time=request.preferred_time,
        call_id=request.call_id,
    )
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/calendar/slots")
async def get_calendar_slots(days: int = 7, max_slots: int = 10):
    calendar = GoogleCalendarService()
    slots = await calendar.get_available_slots(days_ahead=days, max_slots=max_slots)
    return {"slots": slots}
