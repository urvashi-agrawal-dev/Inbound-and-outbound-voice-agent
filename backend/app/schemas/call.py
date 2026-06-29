"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# --- Call Schemas ---

class CallCreateRequest(BaseModel):
    phone_number: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CallCreateResponse(BaseModel):
    call_id: str
    external_call_id: str | None = None
    provider: str
    status: str
    connection: dict[str, Any] | None = None


class UtteranceRequest(BaseModel):
    text: str
    interrupted: bool = False
    audio_url: str | None = None


class UtteranceResponse(BaseModel):
    call_id: str
    response_text: str
    state: str
    lead_data: dict[str, Any]
    scoring: dict[str, Any] | None = None
    latency_ms: float
    should_end: bool = False
    should_book: bool = False
    human_handoff: bool = False
    audio_url: str | None = None


class CallEndRequest(BaseModel):
    reason: str = "completed"


class CallDetailResponse(BaseModel):
    id: UUID
    external_call_id: str | None
    phone_number: str | None
    provider: str
    status: str
    current_state: str
    duration_seconds: float | None
    transcript: str | None
    summary: str | None
    lead_data: dict[str, Any] | None
    scoring: dict[str, Any] | None
    metrics: dict[str, Any] | None
    drop_off_stage: str | None
    qualified: bool
    booked: bool
    human_handoff: bool
    cost_usd: float | None
    avg_latency_ms: float | None
    created_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class CallListResponse(BaseModel):
    calls: list[CallDetailResponse]
    total: int
    page: int
    page_size: int


# --- Lead Schemas ---

class LeadResponse(BaseModel):
    id: UUID
    call_id: UUID
    name: str | None
    company_name: str | None
    industry: str | None
    employee_count: int | None
    email: str | None
    phone: str | None
    lead_score: int | None
    lead_tier: str | None
    crm_synced: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Analytics Schemas ---

class DashboardMetrics(BaseModel):
    total_calls: int
    qualification_rate: float
    booking_rate: float
    avg_duration_seconds: float
    avg_latency_ms: float
    completion_rate: float
    drop_off_stages: dict[str, int]
    cost_per_conversation: float
    active_sessions: int


class AnalyticsTimeSeries(BaseModel):
    date: str
    calls: int
    qualified: int
    booked: int
    avg_latency_ms: float


class AnalyticsResponse(BaseModel):
    metrics: DashboardMetrics
    time_series: list[AnalyticsTimeSeries]
    recent_calls: list[CallDetailResponse]


# --- Webhook Schemas ---

class VapiWebhookEvent(BaseModel):
    message: dict[str, Any]
    call: dict[str, Any] | None = None


class TTSRequest(BaseModel):
    text: str
    call_id: str | None = None


class STTRequest(BaseModel):
    audio_url: str | None = None
    call_id: str | None = None


class BookingRequest(BaseModel):
    call_id: str
    attendee_email: str
    attendee_name: str
    company_name: str
    preferred_time: str | None = None
