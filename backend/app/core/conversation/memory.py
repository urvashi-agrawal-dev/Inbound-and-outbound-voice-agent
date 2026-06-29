"""Conversation memory and context retention across turns."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.core.fsm.states import CollectedLeadData, ConversationState


class ConversationTurn(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state: ConversationState | None = None
    latency_ms: float | None = None
    interrupted: bool = False


class ConversationMemory(BaseModel):
    """Retains full conversation context for a single call session."""

    call_id: str
    turns: list[ConversationTurn] = Field(default_factory=list)
    lead_data: CollectedLeadData = Field(default_factory=CollectedLeadData)
    current_state: ConversationState = ConversationState.INTRO
    previous_state: ConversationState | None = None
    faq_turn_count: int = 0
    interruption_count: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_turn(
        self,
        role: str,
        content: str,
        state: ConversationState | None = None,
        latency_ms: float | None = None,
        interrupted: bool = False,
    ) -> None:
        self.turns.append(
            ConversationTurn(
                role=role,
                content=content,
                state=state or self.current_state,
                latency_ms=latency_ms,
                interrupted=interrupted,
            )
        )

    def get_recent_context(self, max_turns: int = 10) -> list[dict[str, str]]:
        recent = self.turns[-max_turns:]
        return [{"role": t.role, "content": t.content} for t in recent]

    def get_transcript(self) -> str:
        lines = []
        for turn in self.turns:
            speaker = "Caller" if turn.role == "user" else "Agent"
            lines.append(f"{speaker}: {turn.content}")
        return "\n".join(lines)

    def duration_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()

    def merge_extracted_fields(self, fields: dict[str, Any]) -> None:
        for key, value in fields.items():
            if value is not None and hasattr(self.lead_data, key):
                current = getattr(self.lead_data, key)
                if key == "pain_points" and isinstance(value, list):
                    existing = current or []
                    setattr(self.lead_data, key, list(set(existing + value)))
                elif current is None or current == []:
                    setattr(self.lead_data, key, value)
