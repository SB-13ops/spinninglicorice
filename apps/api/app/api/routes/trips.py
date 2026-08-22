"""Concert road-trip planning endpoints.

* GET  /trips/defaults                       - saved trip defaults (origin, MPG, gas).
* PUT  /trips/defaults                       - update them.
* POST /trips/plan/{recommendation_id}       - build a plan + cost estimate for a
                                               scouted concert (origin/mode/nights/etc.
                                               default from saved prefs, overridable).

Read access to the account is required. Estimates use AI web search when enabled;
gas is always computed deterministically. Nothing books or charges anything.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_account_read
from app.db.deps import get_db
from app.models.core import Event, ScoutRecommendation, UserPreference
from app.services.trip_planner import build_trip_plan

router = APIRouter(prefix="/trips", tags=["trips"])

_DEFAULT_KEY = "trip_defaults"


class TripDefaults(BaseModel):
    home_location: str | None = None
    mpg: float = Field(default=28.0, gt=0, le=200)
    gas_price: float | None = Field(default=None, ge=0)
    default_nights: int = Field(default=1, ge=0, le=14)
    default_mode: str = Field(default="compare", pattern="^(drive|fly|compare)$")


def _get_prefs(db: Session, owner_id) -> UserPreference:
    prefs = db.get(UserPreference, owner_id)
    if prefs is None:
        prefs = UserPreference(user_id=owner_id, preferences={})
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.get("/defaults", response_model=TripDefaults)
def get_trip_defaults(ctx=Depends(require_account_read), db: Session = Depends(get_db)):
    prefs = _get_prefs(db, ctx.owner_id)
    stored = (prefs.preferences or {}).get(_DEFAULT_KEY, {})
    # Fall back to the general saved location if no trip-specific origin set.
    if not stored.get("home_location") and prefs.location_text:
        stored = {**stored, "home_location": prefs.location_text}
    return TripDefaults(**stored) if stored else TripDefaults(home_location=prefs.location_text)


@router.put("/defaults", response_model=TripDefaults)
def set_trip_defaults(
    payload: TripDefaults,
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    prefs = _get_prefs(db, ctx.owner_id)
    data = dict(prefs.preferences or {})
    data[_DEFAULT_KEY] = payload.model_dump()
    prefs.preferences = data
    # keep the general location in sync when provided
    if payload.home_location:
        prefs.location_text = payload.home_location
    db.commit()
    return payload


class PlanRequest(BaseModel):
    origin: str | None = None            # overrides saved home_location
    mode: str | None = Field(default=None, pattern="^(drive|fly|compare)$")
    nights: int | None = Field(default=None, ge=0, le=14)
    mpg: float | None = Field(default=None, gt=0, le=200)
    gas_price: float | None = Field(default=None, ge=0)
    travelers: int = Field(default=1, ge=1, le=12)


@router.post("/plan/{recommendation_id}")
def plan_trip(
    recommendation_id: str,
    payload: PlanRequest,
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    try:
        rid = uuid.UUID(recommendation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recommendation id.")

    row = db.execute(
        select(ScoutRecommendation, Event)
        .join(Event, ScoutRecommendation.event_id == Event.id)
        .where(ScoutRecommendation.id == rid, ScoutRecommendation.user_id == ctx.owner_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    _, event = row

    # Merge saved defaults with per-trip overrides.
    defaults = get_trip_defaults(ctx=ctx, db=db)
    origin = payload.origin or defaults.home_location
    if not origin:
        raise HTTPException(
            status_code=400,
            detail="No origin set. Provide an origin or save a home location in trip defaults.",
        )
    dest_city = event.city or (event.region or event.venue_name or "the venue")

    plan = build_trip_plan(
        origin=origin,
        dest_city=dest_city,
        event_name=event.name,
        venue=event.venue_name,
        starts_at=event.starts_at,
        mode=payload.mode or defaults.default_mode,
        nights=payload.nights if payload.nights is not None else defaults.default_nights,
        mpg=payload.mpg or defaults.mpg,
        gas_price=payload.gas_price if payload.gas_price is not None else defaults.gas_price,
        travelers=payload.travelers,
    )
    # dataclass -> dict for JSON
    out = asdict(plan)
    return out
