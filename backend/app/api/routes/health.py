"""Health check endpoints."""

from fastapi import APIRouter

from app import __version__
from app.services.session_store import get_active_session_count

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Karta SDR",
        "version": __version__,
        "active_sessions": get_active_session_count(),
    }


@router.get("/ready")
async def readiness_check():
    return {"status": "ready"}
