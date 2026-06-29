"""Lead management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import LeadRecord
from app.schemas.call import LeadResponse
from app.services.database import get_db

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    tier: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(LeadRecord).order_by(LeadRecord.created_at.desc()).limit(limit)
    if tier:
        stmt = stmt.where(LeadRecord.lead_tier == tier)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(LeadRecord).where(LeadRecord.id == lead_id)
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
