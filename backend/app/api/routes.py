"""
API routes for the SignalDrop backend.
All endpoints serve precomputed data — no heavy processing happens at request time.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..services.trend_service import trend_service

router = APIRouter(prefix="/api")


@router.get("/overview")
def get_overview():
    data = trend_service.get_overview()
    if data is None:
        raise HTTPException(status_code=503, detail="Artifacts not loaded")
    return data


@router.get("/trends")
def get_trends():
    data = trend_service.get_trends()
    if data is None:
        raise HTTPException(status_code=503, detail="Artifacts not loaded")
    return data


@router.get("/trends/{topic}")
def get_trend_detail(topic: str):
    data = trend_service.get_trend_detail(topic)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Trend not found: {topic}")
    return data


@router.get("/channels")
def get_channels(topic: Optional[str] = Query(None)):
    data = trend_service.get_channels(topic)
    if data is None:
        raise HTTPException(status_code=503, detail="Artifacts not loaded")
    return data


@router.get("/methodology")
def get_methodology():
    data = trend_service.get_methodology()
    if data is None:
        raise HTTPException(status_code=503, detail="Artifacts not loaded")
    return data


@router.get("/ai-labels")
def get_ai_labels():
    """Returns AI-generated labels for top trends, or {} if AI labeling was not run."""
    return trend_service.get_ai_labels()


@router.get("/ai-insights")
def get_ai_insights():
    """Returns AI-generated key findings, or {} if AI insights were not generated."""
    return trend_service.get_ai_insights()
