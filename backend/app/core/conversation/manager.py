"""Central conversation orchestrator tying FSM, LLM, and memory together."""

import time
from typing import Any

import structlog

from app.config import get_settings
from app.core.conversation.faq_handler import FAQHandler
from app.core.conversation.interruption import InterruptionHandler
from app.core.conversation.memory import ConversationMemory
from app.core.fsm.states import ConversationState, STATE_PROMPTS
from app.core.fsm.transitions import TransitionEngine
from app.core.scoring.lead_scorer import LeadScorer
from app.services.gemini import GeminiService

logger = structlog.get_logger()


class ConversationManager:
    """
    Orchestrates the full conversation lifecycle:
    STT input → intent detection → field extraction → FSM transition → LLM response
    """

    def __init__(self, call_id: str):
        self.call_id = call_id
        self.memory = ConversationMemory(call_id=call_id)
        self.transitions = TransitionEngine()
        self.faq_handler = FAQHandler()
        self.interruption = InterruptionHandler(
            grace_ms=get_settings().interruption_grace_ms,
            barge_in_enabled=get_settings().barge_in_enabled,
        )
        self.gemini = GeminiService()
        self.scorer = LeadScorer()
        self.settings = get_settings()
        self._total_tokens = 0

    async def process_utterance(
        self,
        user_text: str,
        interrupted: bool = False,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        state = self.memory.current_state

        self.memory.add_turn("user", user_text, state=state, interrupted=interrupted)
        if interrupted:
            self.memory.interruption_count += 1

        intent = self.transitions.detect_intent(user_text)

        extracted = await self.gemini.extract_fields(
            user_text=user_text,
            current_state=state,
            existing_data=self.memory.lead_data.model_dump(),
        )
        self.memory.merge_extracted_fields(extracted.get("fields", {}))
        self._total_tokens += extracted.get("tokens_used", 0)

        if intent == "faq" or state == ConversationState.FAQ_DETOUR:
            self.memory.faq_turn_count += 1
            self.memory.previous_state = (
                self.memory.previous_state or self._get_resume_state()
            )
            response = await self._handle_faq(user_text)
            new_state = ConversationState.FAQ_DETOUR
            if self.faq_handler.should_return_to_flow(
                self.memory.faq_turn_count, self.settings.faq_detour_max_turns
            ):
                new_state = self.transitions._resume_from_detour(self.memory.lead_data)
                self.memory.faq_turn_count = 0
        elif intent == "human_handoff":
            response = await self._handle_human_handoff()
            new_state = ConversationState.HUMAN_HANDOFF
        else:
            new_state = self.transitions.next_state(
                current=state,
                data=self.memory.lead_data,
                intent=intent,
                faq_turns=self.memory.faq_turn_count,
                max_faq_turns=self.settings.faq_detour_max_turns,
            )
            response = await self._generate_state_response(new_state, user_text)

        self.memory.current_state = new_state
        latency_ms = (time.perf_counter() - start) * 1000
        self.memory.add_turn(
            "assistant", response, state=new_state, latency_ms=latency_ms
        )

        scoring = None
        if new_state in (ConversationState.LEAD_SCORING, ConversationState.BOOKING, ConversationState.END_CALL):
            result = self.scorer.score(self.memory.lead_data)
            scoring = {
                "total_score": result.total_score,
                "tier": result.tier.value,
                "breakdown": result.breakdown,
                "qualified_for_booking": result.qualified_for_booking,
            }

        return {
            "response_text": response,
            "state": new_state.value,
            "lead_data": self.memory.lead_data.model_dump(),
            "scoring": scoring,
            "latency_ms": latency_ms,
            "interrupted": interrupted,
            "should_end": new_state == ConversationState.END_CALL,
            "should_book": new_state == ConversationState.BOOKING,
            "human_handoff": new_state == ConversationState.HUMAN_HANDOFF,
        }

    async def get_opening_message(self) -> dict[str, Any]:
        response = await self._generate_state_response(
            ConversationState.INTRO, ""
        )
        self.memory.add_turn("assistant", response, state=ConversationState.INTRO)
        return {
            "response_text": response,
            "state": ConversationState.INTRO.value,
        }

    async def _generate_state_response(
        self, state: ConversationState, user_text: str
    ) -> str:
        state_instruction = STATE_PROMPTS.get(state, "")
        result = await self.gemini.generate_response(
            state=state,
            state_instruction=state_instruction,
            user_text=user_text,
            conversation_history=self.memory.get_recent_context(),
            lead_data=self.memory.lead_data.model_dump(),
        )
        self._total_tokens += result.get("tokens_used", 0)
        return result["text"]

    async def _handle_faq(self, question: str) -> str:
        resume_state = self.memory.previous_state or self._get_resume_state()
        prompt = self.faq_handler.build_faq_prompt(question, resume_state)
        result = await self.gemini.generate_raw(
            prompt=prompt,
            conversation_history=self.memory.get_recent_context(max_turns=6),
        )
        self._total_tokens += result.get("tokens_used", 0)
        return result["text"]

    async def _handle_human_handoff(self) -> str:
        return (
            "Absolutely, I understand you'd like to speak with a human representative. "
            "I'm transferring your information to our sales team now, and someone will "
            "reach out within the next business hour. Is there anything specific "
            "you'd like me to pass along to them?"
        )

    def _get_resume_state(self) -> ConversationState:
        return self.transitions._resume_from_detour(self.memory.lead_data)

    def get_session_metrics(self) -> dict[str, Any]:
        latencies = [
            t.latency_ms for t in self.memory.turns
            if t.latency_ms is not None and t.role == "assistant"
        ]
        return {
            "call_id": self.call_id,
            "duration_seconds": self.memory.duration_seconds(),
            "turn_count": len(self.memory.turns),
            "interruption_count": self.memory.interruption_count,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "completion_percentage": self.memory.lead_data.completion_percentage(),
            "final_state": self.memory.current_state.value,
            "tokens_used": self._total_tokens,
            "estimated_cost_usd": self._estimate_cost(),
        }

    def _estimate_cost(self) -> float:
        duration_min = self.memory.duration_seconds() / 60
        voice_cost = duration_min * self.settings.cost_per_minute_usd
        llm_cost = self._total_tokens * self.settings.cost_per_llm_token_usd
        return round(voice_cost + llm_cost, 4)
