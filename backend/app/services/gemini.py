"""Gemini LLM service for conversation and field extraction."""

import json
import re
from typing import Any

import google.generativeai as genai
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.fsm.states import ConversationState
from app.services.demo_llm import DEMO_RESPONSES, extract_fields_demo, is_demo_mode

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are Alex, an AI sales development representative for Karta SDR.
You conduct professional, warm qualification calls with inbound leads.

RULES:
- Keep responses concise (1-3 sentences) for voice conversation
- Ask ONE question at a time
- Never use markdown, bullet points, or formatting
- Sound natural and conversational, not robotic
- If the caller seems rushed, acknowledge it and be efficient
- Never make up information about the caller
- Stay within the current conversation state objective"""


class GeminiService:
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self.demo = is_demo_mode(settings.gemini_api_key)
        if self.demo:
            logger.warning("gemini_demo_mode", msg="Using offline demo responses (set GEMINI_API_KEY for live LLM)")
            self.model = None
        else:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel(
                model_name=settings.gemini_model,
                system_instruction=SYSTEM_PROMPT,
            )

    async def generate_response(
        self,
        state: ConversationState,
        state_instruction: str,
        user_text: str,
        conversation_history: list[dict[str, str]],
        lead_data: dict[str, Any],
    ) -> dict[str, Any]:
        if self.demo:
            return {"text": DEMO_RESPONSES.get(state, DEMO_RESPONSES[ConversationState.INTRO]), "tokens_used": 0}
        prompt = self._build_conversation_prompt(
            state, state_instruction, user_text, lead_data
        )
        return await self._call_model(prompt, conversation_history)

    async def generate_raw(
        self,
        prompt: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if self.demo:
            return {"text": DEMO_RESPONSES[ConversationState.FAQ_DETOUR], "tokens_used": 0}
        return await self._call_model(prompt, conversation_history or [])

    async def extract_fields(
        self,
        user_text: str,
        current_state: ConversationState,
        existing_data: dict[str, Any],
    ) -> dict[str, Any]:
        if self.demo:
            return {"fields": extract_fields_demo(user_text, current_state), "tokens_used": 0}
        prompt = f"""Extract structured lead data from the caller's message.
Current conversation state: {current_state.value}
Already collected: {json.dumps({k: v for k, v in existing_data.items() if v}, default=str)}

Caller said: "{user_text}"

Return ONLY valid JSON with a "fields" object. Include only fields clearly stated or strongly implied.
Available fields: name, company_name, industry, employee_count (integer),
monthly_inbound_calls (integer), monthly_outbound_calls (integer),
existing_solution, pain_points (array of strings), budget_range, budget_min_usd, budget_max_usd,
timeline, email, phone, permission_to_continue (boolean).

Example: {{"fields": {{"name": "John", "company_name": "Acme Corp"}}}}"""

        result = await self._call_model(prompt, [])
        try:
            text = result["text"]
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                return {"fields": parsed.get("fields", {}), "tokens_used": result.get("tokens_used", 0)}
        except json.JSONDecodeError:
            logger.warning("field_extraction_parse_failed", text=result.get("text", "")[:200])
        return {"fields": {}, "tokens_used": result.get("tokens_used", 0)}

    async def generate_call_summary(
        self, transcript: str, lead_data: dict, scoring: dict | None
    ) -> str:
        if self.demo:
            name = lead_data.get("name", "the caller")
            company = lead_data.get("company_name", "their company")
            tier = scoring.get("tier", "N/A") if scoring else "N/A"
            score = scoring.get("total_score", 0) if scoring else 0
            return (
                f"Demo call with {name} from {company}. "
                f"Lead scored {score} ({tier}). "
                f"Key topics covered: company profile, call volume, pain points, budget, and timeline. "
                f"Recommended next step: schedule demo if qualified."
            )
        prompt = f"""Generate a concise call summary for CRM logging.

Transcript:
{transcript}

Lead Data: {json.dumps(lead_data, default=str)}
Scoring: {json.dumps(scoring, default=str) if scoring else "N/A"}

Include: key findings, qualification status, recommended next steps, and any red flags.
Keep under 200 words. Professional tone."""

        result = await self._call_model(prompt, [])
        return result["text"]

    def _build_conversation_prompt(
        self,
        state: ConversationState,
        state_instruction: str,
        user_text: str,
        lead_data: dict[str, Any],
    ) -> str:
        collected = {k: v for k, v in lead_data.items() if v}
        return f"""Current state: {state.value}
Objective: {state_instruction}
Collected so far: {json.dumps(collected, default=str) if collected else "Nothing yet"}
Caller just said: "{user_text}"

Generate your next spoken response. One question at a time. Be concise for voice."""

    async def _call_model(
        self, prompt: str, history: list[dict[str, str]]
    ) -> dict[str, Any]:
        if self.demo or self.model is None:
            return {"text": "Demo mode response.", "tokens_used": 0}
        contents = []
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            contents.append({"role": role, "parts": [turn["content"]]})
        contents.append({"role": "user", "parts": [prompt]})

        response = await self.model.generate_content_async(
            contents,
            generation_config=genai.GenerationConfig(
                temperature=self.settings.gemini_temperature,
                max_output_tokens=self.settings.gemini_max_tokens,
            ),
        )

        tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens = (
                getattr(response.usage_metadata, "total_token_count", 0) or 0
            )

        return {
            "text": response.text.strip(),
            "tokens_used": tokens,
        }
