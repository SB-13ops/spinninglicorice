"""AI-powered endpoints.

* GET  /ai/status                         - whether AI features are enabled.
* POST /ai/scout/{recommendation_id}/enrich - web-search briefing for a concert
                                             (user-initiated; costs a search).
* POST /ai/pressing/research              - web-search briefing for a pressing.

Enrichment endpoints require account read access and only run when the server
has an Anthropic key configured; otherwise they return 503 so the UI can hide
or disable the button.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_account_read
from app.db.deps import get_db
from app.models.core import Event, ReleaseArtist, Artist, ScoutRecommendation
from app.services.ai.client import get_ai
from app.services.ai.enrichment import enrich_concert, research_pressing

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
def ai_status():
    return {"enabled": get_ai().is_enabled}


@router.post("/scout/{recommendation_id}/enrich")
def enrich_scout(
    recommendation_id: str,
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    if not get_ai().is_enabled:
        raise HTTPException(status_code=503, detail="AI features are not configured.")
    try:
        rid = uuid.UUID(recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation id.")

    row = db.execute(
        select(ScoutRecommendation, Event)
        .join(Event, ScoutRecommendation.event_id == Event.id)
        .where(
            ScoutRecommendation.id == rid,
            ScoutRecommendation.user_id == ctx.owner_id,
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    _, event = row

    result = enrich_concert(
        artist=event.name,  # event.name typically carries the headliner/act
        event_name=event.name,
        venue=event.venue_name,
        city=event.city,
    )
    if result is None:
        raise HTTPException(status_code=502, detail="Enrichment failed. Try again later.")
    return {"text": result.text, "citations": result.citations}


class PressingRequest(BaseModel):
    title: str
    artist: str | None = None
    year: int | None = None
    catalog_number: str | None = None


@router.post("/pressing/research")
def pressing_research(
    payload: PressingRequest,
    ctx=Depends(require_account_read),
):
    if not get_ai().is_enabled:
        raise HTTPException(status_code=503, detail="AI features are not configured.")
    result = research_pressing(
        title=payload.title,
        artist=payload.artist,
        year=payload.year,
        catalog_number=payload.catalog_number,
    )
    if result is None:
        raise HTTPException(status_code=502, detail="Research failed. Try again later.")
    return {"text": result.text, "citations": result.citations}
