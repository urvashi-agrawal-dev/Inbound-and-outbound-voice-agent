"""Call summary generation service."""

from typing import Any

import structlog

from app.services.gemini import GeminiService

logger = structlog.get_logger()


class SummaryService:
    """Generates post-call summaries for CRM and analytics."""

    def __init__(self):
        self.gemini = GeminiService()

    async def generate_summary(
        self,
        transcript: str,
        lead_data: dict[str, Any],
        scoring: dict[str, Any] | None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        summary_text = await self.gemini.generate_call_summary(
            transcript=transcript,
            lead_data=lead_data,
            scoring=scoring,
        )

        return {
            "summary": summary_text,
            "key_findings": self._extract_key_findings(lead_data, scoring),
            "next_steps": self._determine_next_steps(lead_data, scoring),
            "metrics": metrics or {},
        }

    def _extract_key_findings(
        self, lead_data: dict, scoring: dict | None
    ) -> list[str]:
        findings = []
        if lead_data.get("company_name"):
            findings.append(f"Company: {lead_data['company_name']}")
        if lead_data.get("employee_count"):
            findings.append(f"Size: {lead_data['employee_count']} employees")
        inbound = lead_data.get("monthly_inbound_calls", 0) or 0
        outbound = lead_data.get("monthly_outbound_calls", 0) or 0
        if inbound or outbound:
            findings.append(f"Call volume: {inbound + outbound}/month")
        if lead_data.get("pain_points"):
            findings.append(f"Pain points: {', '.join(lead_data['pain_points'][:3])}")
        if scoring:
            findings.append(f"Score: {scoring.get('total_score', 0)} ({scoring.get('tier', 'N/A')})")
        return findings

    def _determine_next_steps(
        self, lead_data: dict, scoring: dict | None
    ) -> list[str]:
        if lead_data.get("wants_human"):
            return ["Human sales rep to follow up within 1 business hour"]
        if lead_data.get("booking_scheduled"):
            return [f"Demo scheduled for {lead_data.get('booking_datetime', 'TBD')}"]
        if scoring and scoring.get("qualified_for_booking"):
            return ["Send demo booking link via email", "Sales rep to follow up within 24h"]
        if scoring and scoring.get("tier") == "Warm Lead":
            return ["Add to nurture campaign", "Follow up in 2 weeks"]
        return ["Log as unqualified", "No immediate follow-up required"]
