"""API router aggregation."""

from fastapi import APIRouter

from app.api.routes import analytics, calls, health, leads, vapi_live, webhooks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(calls.router)
api_router.include_router(vapi_live.router)
api_router.include_router(analytics.router)
api_router.include_router(leads.router)
api_router.include_router(webhooks.router)
