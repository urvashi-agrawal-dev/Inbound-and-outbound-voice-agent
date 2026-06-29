"""Finite state machine conversation states and data models."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConversationState(str, Enum):
    INTRO = "INTRO"
    PERMISSION = "PERMISSION"
    COMPANY_INFO = "COMPANY_INFO"
    CALL_VOLUME = "CALL_VOLUME"
    CURRENT_PROCESS = "CURRENT_PROCESS"
    PAIN_POINTS = "PAIN_POINTS"
    BUDGET = "BUDGET"
    TIMELINE = "TIMELINE"
    LEAD_SCORING = "LEAD_SCORING"
    BOOKING = "BOOKING"
    END_CALL = "END_CALL"
    FAQ_DETOUR = "FAQ_DETOUR"
    HUMAN_HANDOFF = "HUMAN_HANDOFF"


class LeadTier(str, Enum):
    UNQUALIFIED = "Unqualified"
    WARM = "Warm Lead"
    SQL = "Sales Qualified Lead"
    ENTERPRISE = "Priority Enterprise Lead"


class CollectedLeadData(BaseModel):
    """Structured lead information collected during the call."""

    name: str | None = None
    company_name: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    monthly_inbound_calls: int | None = None
    monthly_outbound_calls: int | None = None
    existing_solution: str | None = None
    pain_points: list[str] = Field(default_factory=list)
    budget_range: str | None = None
    budget_min_usd: float | None = None
    budget_max_usd: float | None = None
    timeline: str | None = None
    email: str | None = None
    phone: str | None = None
    permission_to_continue: bool | None = None
    wants_human: bool = False
    booking_scheduled: bool = False
    booking_datetime: str | None = None

    def completion_percentage(self) -> float:
        fields = [
            self.name,
            self.company_name,
            self.industry,
            self.employee_count,
            self.monthly_inbound_calls is not None,
            self.existing_solution,
            self.pain_points,
            self.budget_range,
            self.timeline,
        ]
        filled = sum(1 for f in fields if f)
        return round((filled / len(fields)) * 100, 1)


STATE_PROMPTS: dict[ConversationState, str] = {
    ConversationState.INTRO: (
        "Greet the caller warmly. Introduce yourself as Alex from Karta SDR, "
        "an AI-powered voice sales platform. Ask for their name."
    ),
    ConversationState.PERMISSION: (
        "Confirm you have their name. Explain this is a brief qualification call "
        "(about 5 minutes) to understand their needs. Ask if now is a good time."
    ),
    ConversationState.COMPANY_INFO: (
        "Ask about their company name, industry, and approximate number of employees."
    ),
    ConversationState.CALL_VOLUME: (
        "Ask about their monthly inbound and outbound call volumes. "
        "Get approximate numbers for both."
    ),
    ConversationState.CURRENT_PROCESS: (
        "Ask what solution they currently use for sales calls or lead qualification. "
        "Examples: manual SDRs, outsourced call centers, other AI tools, or none."
    ),
    ConversationState.PAIN_POINTS: (
        "Ask about their biggest challenges with their current sales call process. "
        "Listen for pain around cost, quality, scale, or conversion."
    ),
    ConversationState.BUDGET: (
        "Ask about their budget range for an AI voice solution. "
        "Present ranges: under $500, $500-$2000, $2000-$10000, or $10000+ monthly."
    ),
    ConversationState.TIMELINE: (
        "Ask when they would like to implement a solution: "
        "immediately, within 3 months, 6 months, or 12+ months."
    ),
    ConversationState.LEAD_SCORING: (
        "Thank them for the information. Briefly summarize what you learned "
        "and indicate you're evaluating fit for a demo."
    ),
    ConversationState.BOOKING: (
        "The lead is qualified. Offer to schedule a demo with a sales representative. "
        "Ask for their preferred day and time, and confirm their email."
    ),
    ConversationState.END_CALL: (
        "Thank them for their time. Provide a brief summary and next steps. "
        "End the call professionally."
    ),
    ConversationState.FAQ_DETOUR: (
        "Answer their product or pricing question concisely, then steer back "
        "to the qualification flow."
    ),
    ConversationState.HUMAN_HANDOFF: (
        "Acknowledge their request to speak with a human. "
        "Explain you're connecting them with a representative."
    ),
}

# Ordered flow for main qualification path
QUALIFICATION_FLOW: list[ConversationState] = [
    ConversationState.INTRO,
    ConversationState.PERMISSION,
    ConversationState.COMPANY_INFO,
    ConversationState.CALL_VOLUME,
    ConversationState.CURRENT_PROCESS,
    ConversationState.PAIN_POINTS,
    ConversationState.BUDGET,
    ConversationState.TIMELINE,
    ConversationState.LEAD_SCORING,
    ConversationState.BOOKING,
    ConversationState.END_CALL,
]

REQUIRED_FIELDS_BY_STATE: dict[ConversationState, list[str]] = {
    ConversationState.INTRO: ["name"],
    ConversationState.PERMISSION: ["permission_to_continue"],
    ConversationState.COMPANY_INFO: ["company_name", "industry", "employee_count"],
    ConversationState.CALL_VOLUME: ["monthly_inbound_calls", "monthly_outbound_calls"],
    ConversationState.CURRENT_PROCESS: ["existing_solution"],
    ConversationState.PAIN_POINTS: ["pain_points"],
    ConversationState.BUDGET: ["budget_range"],
    ConversationState.TIMELINE: ["timeline"],
}
