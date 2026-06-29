"""Schemas for Vapi live integration and WebSocket payloads."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class VapiTranscriptRequest(BaseModel):
    call_id: str
    text: str
    role: Literal["user", "assistant"] | None = None
    speaker: Literal["user", "assistant"] | None = None
    interrupted: bool = False
    timestamp: str | None = None
    vapi_mode: bool = True  # When true, skip adding FSM assistant reply to transcript

    @model_validator(mode="after")
    def resolve_role(self) -> "VapiTranscriptRequest":
        if self.role is None and self.speaker is not None:
            object.__setattr__(self, "role", self.speaker)
        if self.role is None:
            raise ValueError("Either role or speaker is required")
        return self


class VapiTranscriptResponse(BaseModel):
    status: str
    state: str
    score: int
    qualified: bool
    tier: str | None = None
    latency_ms: float | None = None
    lead_data: dict[str, Any] | None = None
    qualification_checklist: list[dict[str, Any]] | None = None


class VapiEventRequest(BaseModel):
    call_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class LiveCallResponse(BaseModel):
    call_id: str
    status: str
    connection_status: str
    speaking_role: str | None
    current_state: str
    lead_data: dict[str, Any]
    scoring: dict[str, Any] | None
    transcript: list[dict[str, Any]]
    state_transitions: list[dict[str, Any]]
    score_history: list[dict[str, Any]]
    qualification_checklist: list[dict[str, Any]]
    duration_seconds: float
    cost_usd: float
    avg_latency_ms: float
    tokens_used: int


class CallSummaryResponse(BaseModel):
    call_id: str
    status: str
    summary: str | None
    key_findings: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    scoring: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    recommended_action: str | None = None
