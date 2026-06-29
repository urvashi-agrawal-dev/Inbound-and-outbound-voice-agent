"""In-memory live call state for real-time dashboard updates."""

from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.core.fsm.states import QUALIFICATION_FLOW, ConversationState, REQUIRED_FIELDS_BY_STATE
from app.core.scoring.lead_scorer import LeadScorer


class LiveCallState:
    """Tracks live metrics, transcript, and state history for an active call."""

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.started_at = datetime.now(timezone.utc)
        self.transcript: list[dict[str, Any]] = []
        self.state_transitions: list[dict[str, Any]] = []
        self.score_history: list[dict[str, Any]] = []
        self.current_state = ConversationState.INTRO.value
        self.lead_data: dict[str, Any] = {}
        self.scoring: dict[str, Any] | None = None
        self.latency_samples: list[float] = []
        self.tokens_used = 0
        self.connection_status = "connecting"
        self.speaking_role: str | None = None  # "assistant" | "user"
        self.summary: dict[str, Any] | None = None
        self.status = "active"

    def add_transcript(self, role: str, text: str, state: str | None = None) -> dict:
        entry = {
            "role": role,
            "text": text,
            "state": state or self.current_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.transcript.append(entry)
        return entry

    def record_state_change(self, new_state: str, previous: str | None = None) -> None:
        if new_state == self.current_state and not previous:
            return
        self.state_transitions.append({
            "from": previous or self.current_state,
            "to": new_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.current_state = new_state

    def update_from_utterance(
        self,
        result: dict[str, Any],
        role: str = "user",
    ) -> None:
        if role == "user":
            self.lead_data = result.get("lead_data", self.lead_data)
            prev = self.current_state
            new_state = result.get("state", self.current_state)
            self.record_state_change(new_state, prev)
            if result.get("latency_ms"):
                self.latency_samples.append(result["latency_ms"])
        if result.get("scoring"):
            self.scoring = result["scoring"]
            self.score_history.append({
                "score": result["scoring"].get("total_score"),
                "tier": result["scoring"].get("tier"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        else:
            from app.core.fsm.states import CollectedLeadData
            data = CollectedLeadData(**{
                k: v for k, v in self.lead_data.items()
                if k in CollectedLeadData.model_fields
            })
            result = LeadScorer().score(data)
            self.scoring = {
                "total_score": result.total_score,
                "tier": result.tier.value,
                "breakdown": result.breakdown,
                "qualified_for_booking": result.qualified_for_booking,
            }
            self.score_history.append({
                "score": result.total_score,
                "tier": result.tier.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    def duration_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()

    def estimated_cost(self) -> float:
        settings = get_settings()
        minutes = self.duration_seconds() / 60
        return round(
            minutes * settings.cost_per_minute_usd
            + self.tokens_used * settings.cost_per_llm_token_usd,
            4,
        )

    def avg_latency_ms(self) -> float:
        if not self.latency_samples:
            return 0.0
        return round(sum(self.latency_samples) / len(self.latency_samples), 1)

    def qualification_checklist(self) -> list[dict[str, Any]]:
        labels = {
            ConversationState.COMPANY_INFO: "Company Information",
            ConversationState.CALL_VOLUME: "Call Volume",
            ConversationState.CURRENT_PROCESS: "Current Process",
            ConversationState.PAIN_POINTS: "Pain Points",
            ConversationState.BUDGET: "Budget",
            ConversationState.TIMELINE: "Timeline",
        }
        from app.core.fsm.states import CollectedLeadData
        from app.core.fsm.transitions import TransitionEngine

        data = CollectedLeadData(**{k: v for k, v in self.lead_data.items() if v is not None})
        engine = TransitionEngine()
        items = []
        for state in [
            ConversationState.COMPANY_INFO,
            ConversationState.CALL_VOLUME,
            ConversationState.CURRENT_PROCESS,
            ConversationState.PAIN_POINTS,
            ConversationState.BUDGET,
            ConversationState.TIMELINE,
        ]:
            complete = engine.is_state_complete(state, data)
            items.append({
                "state": state.value,
                "label": labels[state],
                "complete": complete,
            })
        return items

    def to_live_payload(self) -> dict[str, Any]:
        scorer = LeadScorer()
        from app.core.fsm.states import CollectedLeadData

        data = CollectedLeadData(**{
            k: v for k, v in self.lead_data.items()
            if k in CollectedLeadData.model_fields
        })
        live_scoring = self.scoring
        if not live_scoring and any(self.lead_data.values()):
            result = scorer.score(data)
            live_scoring = {
                "total_score": result.total_score,
                "tier": result.tier.value,
                "breakdown": result.breakdown,
                "qualified_for_booking": result.qualified_for_booking,
            }

        return {
            "call_id": self.call_id,
            "status": self.status,
            "connection_status": self.connection_status,
            "speaking_role": self.speaking_role,
            "current_state": self.current_state,
            "lead_data": self.lead_data,
            "scoring": live_scoring,
            "transcript": self.transcript,
            "state_transitions": self.state_transitions,
            "score_history": self.score_history,
            "qualification_checklist": self.qualification_checklist(),
            "duration_seconds": round(self.duration_seconds(), 1),
            "cost_usd": self.estimated_cost(),
            "avg_latency_ms": self.avg_latency_ms(),
            "tokens_used": self.tokens_used,
        }


_live_states: dict[str, LiveCallState] = {}


def get_live_state(call_id: str) -> LiveCallState:
    if call_id not in _live_states:
        _live_states[call_id] = LiveCallState(call_id)
    return _live_states[call_id]


def remove_live_state(call_id: str) -> LiveCallState | None:
    return _live_states.pop(call_id, None)
