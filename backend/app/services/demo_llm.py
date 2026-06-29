"""Offline demo responses when Gemini API key is not configured."""

import re
from typing import Any

from app.core.fsm.states import ConversationState

DEMO_RESPONSES: dict[ConversationState, str] = {
    ConversationState.INTRO: (
        "Hi there! This is Alex from Karta SDR. Thanks for reaching out. "
        "May I ask who I'm speaking with today?"
    ),
    ConversationState.PERMISSION: (
        "Great to meet you! This will be a quick five-minute qualification call. "
        "Is now a good time to chat?"
    ),
    ConversationState.COMPANY_INFO: (
        "Perfect. Can you tell me your company name, what industry you're in, "
        "and roughly how many employees you have?"
    ),
    ConversationState.CALL_VOLUME: (
        "Got it. What are your approximate monthly inbound and outbound call volumes?"
    ),
    ConversationState.CURRENT_PROCESS: (
        "Thanks. What are you currently using for sales calls or lead qualification?"
    ),
    ConversationState.PAIN_POINTS: (
        "What are the biggest challenges with your current approach?"
    ),
    ConversationState.BUDGET: (
        "What monthly budget range are you considering for an AI voice solution? "
        "For example, under five hundred, five hundred to two thousand, two to ten thousand, or above ten thousand?"
    ),
    ConversationState.TIMELINE: (
        "When are you looking to implement — immediately, within three months, six months, or longer?"
    ),
    ConversationState.LEAD_SCORING: (
        "Thank you for sharing all of that. Based on what you've told me, "
        "I think Karta SDR could be a strong fit for your team."
    ),
    ConversationState.BOOKING: (
        "I'd love to set up a demo with our sales team. "
        "What day and time works best, and what's the best email to send the invite?"
    ),
    ConversationState.END_CALL: (
        "Thank you so much for your time today. We'll be in touch with next steps. Have a great day!"
    ),
    ConversationState.FAQ_DETOUR: (
        "Our plans start at four ninety-nine per month for up to a thousand calls. "
        "Now, let me get back to understanding your needs."
    ),
    ConversationState.HUMAN_HANDOFF: (
        "Of course — I'll have a human representative follow up with you shortly."
    ),
}


def extract_fields_demo(user_text: str, state: ConversationState) -> dict[str, Any]:
    """Rule-based field extraction for local demo mode."""
    text = user_text.lower()
    fields: dict[str, Any] = {}

    name_match = re.search(
        r"(?:i'm|i am|my name is|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        user_text,
        re.I,
    )
    if name_match:
        fields["name"] = name_match.group(1).strip().title()

    if re.search(r"we are\s+([^,]+)", user_text, re.I):
        fields["company_name"] = re.search(r"we are\s+([^,]+)", user_text, re.I).group(1).strip()
    elif "techflow" in text:
        fields["company_name"] = "TechFlow"

    if "saas" in text:
        fields["industry"] = "SaaS"
    emp_match = re.search(r"(\d+)\s*employees?", text)
    if emp_match:
        fields["employee_count"] = int(emp_match.group(1))

    inbound = re.search(r"(\d[\d,]*)\s*inbound", text)
    outbound = re.search(r"(\d[\d,]*)\s*outbound", text)
    if inbound:
        fields["monthly_inbound_calls"] = int(inbound.group(1).replace(",", ""))
    if outbound:
        fields["monthly_outbound_calls"] = int(outbound.group(1).replace(",", ""))
    vol_match = re.search(r"(\d[\d,]+)\s*(?:calls?|per month)", text)
    if vol_match and "monthly_inbound_calls" not in fields:
        fields["monthly_inbound_calls"] = int(vol_match.group(1).replace(",", ""))

    if any(w in text for w in ["yes", "sure", "go ahead", "good time", "works"]):
        if state == ConversationState.PERMISSION:
            fields["permission_to_continue"] = True

    if "manual" in text or "sdr" in text:
        fields["existing_solution"] = "manual SDR team"
    if any(w in text for w in ["cost", "expensive", "inconsistent", "challenge"]):
        fields["pain_points"] = ["high cost", "inconsistent qualification"]

    if "2000" in text or "2,000" in text or "ten thousand" in text or "10000" in text:
        fields["budget_range"] = "$2000-$10000"
        fields["budget_min_usd"] = 2000
        fields["budget_max_usd"] = 10000
    elif "500" in text:
        fields["budget_range"] = "$500-$2000"

    if "3 month" in text or "three month" in text or "quarter" in text:
        fields["timeline"] = "3 months"
    elif "immediate" in text or "asap" in text:
        fields["timeline"] = "immediate"

    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", user_text)
    if email_match:
        fields["email"] = email_match.group(0)

    if "tuesday" in text or "demo" in text or "schedule" in text:
        fields["booking_scheduled"] = True
        fields["booking_datetime"] = "Tuesday 2pm"

    return fields


def is_demo_mode(api_key: str) -> bool:
    return not api_key or api_key.startswith("your-") or api_key == "demo-mode"
