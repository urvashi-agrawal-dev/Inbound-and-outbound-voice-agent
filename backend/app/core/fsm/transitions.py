"""FSM transition logic and state advancement rules."""

import re

from app.core.fsm.states import (
    REQUIRED_FIELDS_BY_STATE,
    QUALIFICATION_FLOW,
    CollectedLeadData,
    ConversationState,
    LeadTier,
)
from app.core.scoring.lead_scorer import LeadScorer


class TransitionEngine:
    """Determines valid state transitions based on collected data and intents."""

    HUMAN_REQUEST_KEYWORDS = [
        "human", "person", "representative", "agent", "real person",
        "speak to someone", "talk to someone", "manager", "sales rep",
    ]

    FAQ_KEYWORDS = [
        "pricing", "price", "cost", "how much", "what do you do",
        "how does it work", "features", "product", "integration",
        "security", "compliance", "hipaa", "gdpr",
    ]

    FAQ_EXCLUDED_STATES = {
        ConversationState.PAIN_POINTS,
        ConversationState.BUDGET,
        ConversationState.TIMELINE,
        ConversationState.COMPANY_INFO,
        ConversationState.CALL_VOLUME,
        ConversationState.CURRENT_PROCESS,
        ConversationState.PERMISSION,
        ConversationState.BOOKING,
    }

    _END_CALL_RE = re.compile(
        r"\b(no|not interested|stop|goodbye|bye)\b", re.IGNORECASE
    )
    _AFFIRMATIVE_RE = re.compile(
        r"\b(yes|yeah|yep|sure|okay|ok|go ahead|sounds good|good time)\b",
        re.IGNORECASE,
    )

    def detect_intent(self, user_text: str) -> str:
        text = user_text.lower()
        if re.search(
            r"\b(" + "|".join(re.escape(k) for k in self.HUMAN_REQUEST_KEYWORDS) + r")\b",
            text,
        ):
            return "human_handoff"
        if self._is_faq_question(text):
            return "faq"
        if self._END_CALL_RE.search(text):
            return "end_call"
        if self._AFFIRMATIVE_RE.search(text):
            return "affirmative"
        return "continue"

    def _is_faq_question(self, text: str) -> bool:
        if not any(kw in text for kw in self.FAQ_KEYWORDS):
            return False
        return "?" in text or text.strip().startswith(
            ("how", "what", "tell me", "can you explain", "do you")
        )

    def is_state_complete(
        self, state: ConversationState, data: CollectedLeadData
    ) -> bool:
        required = REQUIRED_FIELDS_BY_STATE.get(state, [])
        for field in required:
            value = getattr(data, field, None)
            if value is None:
                return False
            if field == "pain_points" and not value:
                return False
            if field == "permission_to_continue" and value is False:
                return True  # Explicit decline is a valid completion
        return True

    def next_state(
        self,
        current: ConversationState,
        data: CollectedLeadData,
        intent: str,
        faq_turns: int = 0,
        max_faq_turns: int = 3,
    ) -> ConversationState:
        if intent == "human_handoff":
            data.wants_human = True
            return ConversationState.HUMAN_HANDOFF

        if intent == "end_call":
            return ConversationState.END_CALL

        if current == ConversationState.FAQ_DETOUR:
            if faq_turns >= max_faq_turns:
                return self._resume_from_detour(data)
            return ConversationState.FAQ_DETOUR

        if intent == "faq" and current not in (
            ConversationState.LEAD_SCORING,
            ConversationState.END_CALL,
            *self.FAQ_EXCLUDED_STATES,
        ):
            return ConversationState.FAQ_DETOUR

        if current == ConversationState.PERMISSION and data.permission_to_continue is False:
            return ConversationState.END_CALL

        if not self.is_state_complete(current, data):
            return current

        return self._advance_in_flow(current, data)

    def _resume_from_detour(self, data: CollectedLeadData) -> ConversationState:
        for state in reversed(QUALIFICATION_FLOW):
            if not self.is_state_complete(state, data):
                return state
        return ConversationState.LEAD_SCORING

    def _advance_in_flow(
        self, current: ConversationState, data: CollectedLeadData
    ) -> ConversationState:
        try:
            idx = QUALIFICATION_FLOW.index(current)
        except ValueError:
            return ConversationState.END_CALL

        if current == ConversationState.LEAD_SCORING:
            tier = LeadScorer().score(data).tier
            if tier in (LeadTier.SQL, LeadTier.ENTERPRISE):
                return ConversationState.BOOKING
            return ConversationState.END_CALL

        if current == ConversationState.BOOKING and data.booking_scheduled:
            return ConversationState.END_CALL

        if idx + 1 < len(QUALIFICATION_FLOW):
            return QUALIFICATION_FLOW[idx + 1]
        return ConversationState.END_CALL

    def get_drop_off_stage(self, state: ConversationState) -> str:
        return state.value
