"""Lead scoring engine with configurable point thresholds."""

from dataclasses import dataclass

from app.core.fsm.states import CollectedLeadData, LeadTier
from app.config import get_settings


@dataclass
class ScoringResult:
    total_score: int
    tier: LeadTier
    breakdown: dict[str, int]
    qualified_for_booking: bool


class LeadScorer:
    """Scores leads based on company size, call volume, budget, and timeline."""

    def score(self, data: CollectedLeadData) -> ScoringResult:
        breakdown = {
            "company_size": self._score_company_size(data.employee_count),
            "call_volume": self._score_call_volume(
                data.monthly_inbound_calls, data.monthly_outbound_calls
            ),
            "budget": self._score_budget(data.budget_min_usd, data.budget_max_usd, data.budget_range),
            "timeline": self._score_timeline(data.timeline),
        }
        total = sum(breakdown.values())
        tier = self._classify_tier(total)
        settings = get_settings()
        qualified = total > settings.score_unqualified_max

        return ScoringResult(
            total_score=total,
            tier=tier,
            breakdown=breakdown,
            qualified_for_booking=qualified and tier in (
                LeadTier.SQL,
                LeadTier.ENTERPRISE,
            ),
        )

    def _score_company_size(self, employees: int | None) -> int:
        if employees is None:
            return 0
        if employees <= 10:
            return 5
        if employees <= 50:
            return 15
        if employees <= 200:
            return 25
        return 40

    def _score_call_volume(
        self, inbound: int | None, outbound: int | None
    ) -> int:
        total = (inbound or 0) + (outbound or 0)
        if total < 1000:
            return 5
        if total < 10000:
            return 20
        if total < 50000:
            return 35
        return 50

    def _score_budget(
        self,
        min_usd: float | None,
        max_usd: float | None,
        range_str: str | None,
    ) -> int:
        if min_usd is not None or max_usd is not None:
            avg = ((min_usd or 0) + (max_usd or min_usd or 0)) / (
                2 if min_usd and max_usd else 1
            )
            if avg < 500:
                return 0
            if avg < 2000:
                return 15
            if avg < 10000:
                return 30
            return 40

        if not range_str:
            return 0
        text = range_str.lower()
        if "10000" in text or "10,000" in text or "10k+" in text or "more than" in text:
            return 40
        if "2000" in text or "2,000" in text or "2k" in text:
            if "10000" in text or "10k" in text:
                return 30
            return 30 if "to" in text or "-" in text else 15
        if "500" in text:
            return 15 if "to" in text or "-" in text or "2000" in text else 0
        return 0

    def _score_timeline(self, timeline: str | None) -> int:
        if not timeline:
            return 0
        text = timeline.lower()
        if any(w in text for w in ["immediate", "asap", "now", "right away", "this week"]):
            return 30
        if "3 month" in text or "three month" in text or "quarter" in text:
            return 20
        if "6 month" in text or "six month" in text or "half year" in text:
            return 10
        return 0

    def _classify_tier(self, score: int) -> LeadTier:
        settings = get_settings()
        if score <= settings.score_unqualified_max:
            return LeadTier.UNQUALIFIED
        if score <= settings.score_warm_max:
            return LeadTier.WARM
        if score <= settings.score_sql_max:
            return LeadTier.SQL
        return LeadTier.ENTERPRISE
