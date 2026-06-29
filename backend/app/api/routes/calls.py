"""Call management API endpoints."""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.scoring.lead_scorer import LeadScorer
from app.models.call import CallRecord, LeadRecord
from app.schemas.call import (
    CallCreateRequest,
    CallCreateResponse,
    CallDetailResponse,
    CallEndRequest,
    CallListResponse,
    UtteranceRequest,
    UtteranceResponse,
)
from app.services.database import get_db
from app.services.edge_tts import EdgeTTSService
from app.services.google_calendar import GoogleCalendarService
from app.services.google_sheets import GoogleSheetsCRM
from app.services.live_call_state import get_live_state, remove_live_state
from app.services.session_store import get_or_create_session, remove_session
from app.services.summary import SummaryService
from app.services.voice_orchestrator import VoiceOrchestrator
from app.services.websocket_manager import ws_manager
from app.services.whisper import WhisperService
from app.schemas.vapi_live import CallSummaryResponse, LiveCallResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("", response_model=CallCreateResponse)
async def create_call(
    request: CallCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    call_id = str(uuid.uuid4())
    orchestrator = VoiceOrchestrator()

    try:
        result = await orchestrator.initiate_call(
            phone_number=request.phone_number,
            call_id=call_id,
            metadata=request.metadata,
        )
    except Exception as e:
        logger.warning("voice_init_fallback", error=str(e))
        result = {
            "provider": get_settings().voice_provider,
            "external_call_id": None,
            "status": "simulated",
            "connection": None,
        }

    call_record = CallRecord(
        id=uuid.UUID(call_id),
        external_call_id=result.get("external_call_id"),
        phone_number=request.phone_number,
        provider=result.get("provider", "simulated"),
        status=result.get("status", "active"),
    )
    db.add(call_record)
    await db.flush()

    manager = await get_or_create_session(call_id)
    await manager.get_opening_message()
    live = get_live_state(call_id)
    live.connection_status = "ready"
    live.status = "active"

    return CallCreateResponse(
        call_id=call_id,
        external_call_id=result.get("external_call_id"),
        provider=result["provider"],
        status=result["status"],
        connection=result.get("connection"),
    )


@router.post("/{call_id}/utterance", response_model=UtteranceResponse)
async def process_utterance(
    call_id: str,
    request: UtteranceRequest,
    db: AsyncSession = Depends(get_db),
):
    manager = await get_or_create_session(call_id)
    result = await manager.process_utterance(
        user_text=request.text,
        interrupted=request.interrupted,
    )

    result_uuid = uuid.UUID(call_id)
    stmt = select(CallRecord).where(CallRecord.id == result_uuid)
    db_result = await db.execute(stmt)
    call_record = db_result.scalar_one_or_none()
    if call_record:
        call_record.current_state = result["state"]
        call_record.lead_data = result["lead_data"]
        if result.get("scoring"):
            call_record.scoring = result["scoring"]
            call_record.qualified = result["scoring"].get("qualified_for_booking", False)

    tts = EdgeTTSService()
    try:
        await tts.synthesize(result["response_text"])
    except Exception as e:
        logger.warning("tts_synthesis_failed", error=str(e))

    live = get_live_state(call_id)
    live.update_from_utterance(result, role="user")
    live.add_transcript("user", request.text, result["state"])
    live.add_transcript("assistant", result["response_text"], result["state"])
    await ws_manager.broadcast(call_id, "utterance_processed", live.to_live_payload())

    return UtteranceResponse(
        call_id=call_id,
        response_text=result["response_text"],
        state=result["state"],
        lead_data=result["lead_data"],
        scoring=result.get("scoring"),
        latency_ms=result["latency_ms"],
        should_end=result.get("should_end", False),
        should_book=result.get("should_book", False),
        human_handoff=result.get("human_handoff", False),
    )


@router.post("/{call_id}/audio")
async def process_audio_utterance(
    call_id: str,
    audio: UploadFile = File(...),
    interrupted: bool = False,
    db: AsyncSession = Depends(get_db),
):
    whisper = WhisperService()
    audio_data = await audio.read()
    transcription = await whisper.transcribe(audio_data, filename=audio.filename or "audio.wav")

    request = UtteranceRequest(text=transcription["text"], interrupted=interrupted)
    return await process_utterance(call_id, request, db)


@router.post("/{call_id}/end")
async def end_call(
    call_id: str,
    request: CallEndRequest,
    db: AsyncSession = Depends(get_db),
):
    manager = await remove_session(call_id)
    if not manager:
        raise HTTPException(status_code=404, detail="Call session not found")

    metrics = manager.get_session_metrics()
    scoring_result = LeadScorer().score(manager.memory.lead_data)
    scoring = {
        "total_score": scoring_result.total_score,
        "tier": scoring_result.tier.value,
        "breakdown": scoring_result.breakdown,
        "qualified_for_booking": scoring_result.qualified_for_booking,
    }

    summary_service = SummaryService()
    summary_result = await summary_service.generate_summary(
        transcript=manager.memory.get_transcript(),
        lead_data=manager.memory.lead_data.model_dump(),
        scoring=scoring,
        metrics=metrics,
    )

    result_uuid = uuid.UUID(call_id)
    stmt = select(CallRecord).where(CallRecord.id == result_uuid)
    db_result = await db.execute(stmt)
    call_record = db_result.scalar_one_or_none()
    if call_record:
        call_record.status = "completed"
        call_record.ended_at = datetime.now(timezone.utc)
        call_record.duration_seconds = metrics["duration_seconds"]
        call_record.transcript = manager.memory.get_transcript()
        call_record.summary = summary_result["summary"]
        call_record.lead_data = manager.memory.lead_data.model_dump()
        call_record.scoring = scoring
        call_record.metrics = metrics
        call_record.qualified = scoring_result.qualified_for_booking
        call_record.booked = manager.memory.lead_data.booking_scheduled
        call_record.human_handoff = manager.memory.lead_data.wants_human
        call_record.cost_usd = metrics["estimated_cost_usd"]
        call_record.avg_latency_ms = metrics["avg_latency_ms"]
        call_record.interruption_count = metrics["interruption_count"]
        call_record.drop_off_stage = manager.memory.current_state.value

        lead = LeadRecord(
            call_id=result_uuid,
            name=manager.memory.lead_data.name,
            company_name=manager.memory.lead_data.company_name,
            industry=manager.memory.lead_data.industry,
            employee_count=manager.memory.lead_data.employee_count,
            email=manager.memory.lead_data.email,
            phone=manager.memory.lead_data.phone,
            lead_score=scoring_result.total_score,
            lead_tier=scoring_result.tier.value,
        )
        db.add(lead)

    crm = GoogleSheetsCRM()
    await crm.create_lead_record(
        call_id=call_id,
        lead_data=manager.memory.lead_data.model_dump(),
        scoring=scoring,
        summary=summary_result["summary"],
        duration_seconds=metrics["duration_seconds"],
    )

    live = remove_live_state(call_id)
    if live:
        live.status = "completed"
        live.summary = summary_result
        await ws_manager.broadcast(call_id, "call_ended", {
            **live.to_live_payload(),
            "summary": summary_result,
            "scoring": scoring,
        })

    return {
        "call_id": call_id,
        "status": "completed",
        "summary": summary_result,
        "scoring": scoring,
        "metrics": metrics,
    }


@router.get("/{call_id}/live", response_model=LiveCallResponse)
async def get_call_live(call_id: str):
    live = get_live_state(call_id)
    return LiveCallResponse(**live.to_live_payload())


def _recommended_action(scoring: dict | None) -> str:
    if not scoring:
        return "Continue qualification"
    if scoring.get("qualified_for_booking"):
        return "Schedule Demo"
    tier = scoring.get("tier", "")
    if tier == "Warm Lead":
        return "Add to nurture campaign"
    if tier == "Priority Enterprise Lead":
        return "Priority sales follow-up"
    return "Log and review"


@router.get("/{call_id}/summary", response_model=CallSummaryResponse)
async def get_call_summary_endpoint(call_id: str, db: AsyncSession = Depends(get_db)):
    try:
        call_uuid = uuid.UUID(call_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call_id")

    stmt = select(CallRecord).where(CallRecord.id == call_uuid)
    db_result = await db.execute(stmt)
    call_record = db_result.scalar_one_or_none()

    if call_record and call_record.status == "completed" and call_record.summary:
        scoring = call_record.scoring or {}
        return CallSummaryResponse(
            call_id=call_id,
            status="completed",
            summary=call_record.summary,
            scoring=scoring,
            metrics=call_record.metrics,
            recommended_action=_recommended_action(scoring),
        )

    live = get_live_state(call_id)
    try:
        manager = await get_or_create_session(call_id)
    except Exception:
        manager = None

    if manager:
        scoring_result = LeadScorer().score(manager.memory.lead_data)
        scoring = {
            "total_score": scoring_result.total_score,
            "tier": scoring_result.tier.value,
            "breakdown": scoring_result.breakdown,
            "qualified_for_booking": scoring_result.qualified_for_booking,
        }
        summary_service = SummaryService()
        transcript_text = manager.memory.get_transcript()
        if live.transcript:
            transcript_text = "\n".join(
                f"{'Caller' if t['role'] == 'user' else 'Agent'}: {t['text']}"
                for t in live.transcript
            )
        summary_result = await summary_service.generate_summary(
            transcript=transcript_text,
            lead_data=manager.memory.lead_data.model_dump(),
            scoring=scoring,
            metrics=manager.get_session_metrics(),
        )
        return CallSummaryResponse(
            call_id=call_id,
            status=live.status,
            summary=summary_result.get("summary"),
            key_findings=summary_result.get("key_findings", []),
            next_steps=summary_result.get("next_steps", []),
            scoring=scoring,
            metrics=manager.get_session_metrics(),
            recommended_action=_recommended_action(scoring),
        )

    return CallSummaryResponse(
        call_id=call_id,
        status="unknown",
        summary=None,
        recommended_action="Continue qualification",
    )


@router.get("/{call_id}", response_model=CallDetailResponse)
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)):
    result_uuid = uuid.UUID(call_id)
    stmt = select(CallRecord).where(CallRecord.id == result_uuid)
    db_result = await db.execute(stmt)
    call_record = db_result.scalar_one_or_none()
    if not call_record:
        raise HTTPException(status_code=404, detail="Call not found")
    return call_record


@router.get("", response_model=CallListResponse)
async def list_calls(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    count_stmt = select(func.count()).select_from(CallRecord)
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(CallRecord)
        .order_by(CallRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    calls = result.scalars().all()

    return CallListResponse(
        calls=calls,
        total=total,
        page=page,
        page_size=page_size,
    )
