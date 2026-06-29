"""Analytics dashboard API endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import CallRecord
from app.schemas.call import (
    AnalyticsResponse,
    AnalyticsTimeSeries,
    CallDetailResponse,
    DashboardMetrics,
)
from app.services.database import get_db
from app.services.session_store import get_active_session_count

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=AnalyticsResponse)
async def get_dashboard(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = select(CallRecord).where(
        CallRecord.created_at >= since,
        CallRecord.status == "completed",
    )
    result = await db.execute(stmt)
    calls = result.scalars().all()

    total = len(calls)
    qualified = sum(1 for c in calls if c.qualified)
    booked = sum(1 for c in calls if c.booked)
    completed = sum(1 for c in calls if c.duration_seconds and c.duration_seconds > 60)

    durations = [c.duration_seconds for c in calls if c.duration_seconds]
    latencies = [c.avg_latency_ms for c in calls if c.avg_latency_ms]
    costs = [c.cost_usd for c in calls if c.cost_usd]

    drop_offs: dict[str, int] = {}
    for c in calls:
        if c.drop_off_stage and not c.qualified:
            drop_offs[c.drop_off_stage] = drop_offs.get(c.drop_off_stage, 0) + 1

    metrics = DashboardMetrics(
        total_calls=total,
        qualification_rate=round(qualified / total * 100, 1) if total else 0,
        booking_rate=round(booked / total * 100, 1) if total else 0,
        avg_duration_seconds=round(sum(durations) / len(durations), 1) if durations else 0,
        avg_latency_ms=round(sum(latencies) / len(latencies), 1) if latencies else 0,
        completion_rate=round(completed / total * 100, 1) if total else 0,
        drop_off_stages=drop_offs,
        cost_per_conversation=round(sum(costs) / len(costs), 4) if costs else 0,
        active_sessions=get_active_session_count(),
    )

    time_series = _build_time_series(calls, days)

    recent_stmt = (
        select(CallRecord)
        .order_by(CallRecord.created_at.desc())
        .limit(10)
    )
    recent_result = await db.execute(recent_stmt)
    recent_calls = recent_result.scalars().all()

    return AnalyticsResponse(
        metrics=metrics,
        time_series=time_series,
        recent_calls=[CallDetailResponse.model_validate(c) for c in recent_calls],
    )


def _build_time_series(calls: list, days: int) -> list[AnalyticsTimeSeries]:
    buckets: dict[str, dict] = {}
    for i in range(days):
        date = (datetime.now(timezone.utc) - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        buckets[date] = {"calls": 0, "qualified": 0, "booked": 0, "latencies": []}

    for call in calls:
        date_key = call.created_at.strftime("%Y-%m-%d")
        if date_key in buckets:
            buckets[date_key]["calls"] += 1
            if call.qualified:
                buckets[date_key]["qualified"] += 1
            if call.booked:
                buckets[date_key]["booked"] += 1
            if call.avg_latency_ms:
                buckets[date_key]["latencies"].append(call.avg_latency_ms)

    return [
        AnalyticsTimeSeries(
            date=date,
            calls=data["calls"],
            qualified=data["qualified"],
            booked=data["booked"],
            avg_latency_ms=round(
                sum(data["latencies"]) / len(data["latencies"]), 1
            ) if data["latencies"] else 0,
        )
        for date, data in sorted(buckets.items())
    ]
