"""Collection insights: value tracking and completion.

* GET  /insights/value             - current worth, history, best/worst movers.
* POST /insights/value/snapshot    - capture a snapshot now (write; admin/owner).
* GET  /insights/completion        - complete-the-collection gaps by artist.

Reads require account read; capturing a snapshot requires write.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.db.deps import get_db
from app.models.core import User
from app.services.collector_card import build_collector_card
from app.services.completion import artist_completion
from app.services.valuation import capture_snapshot, get_value_summary

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/value")
def value_summary(ctx=Depends(require_account_read), db: Session = Depends(get_db)):
    return get_value_summary(db, ctx.owner_id)


@router.post("/value/snapshot")
def take_snapshot(ctx=Depends(require_account_write), db: Session = Depends(get_db)):
    snap = capture_snapshot(db, ctx.owner_id)
    return {
        "captured_at": snap.captured_at.isoformat(),
        "total_value": float(snap.total_value),
        "item_count": snap.item_count,
        "valued_count": snap.valued_count,
    }


@router.get("/completion")
def completion(ctx=Depends(require_account_read), db: Session = Depends(get_db)):
    return {"artists": artist_completion(db, ctx.owner_id)}


@router.get("/card")
def collector_card(ctx=Depends(require_account_read), db: Session = Depends(get_db)):
    """A shareable Collector Card as an SVG image (genres/labels, era, rarity,
    worth). Renders directly in an <img> or can be converted to PNG client-side."""
    owner = db.get(User, ctx.owner_id)
    name = (owner.display_name if owner and owner.display_name else None)
    svg = build_collector_card(db, ctx.owner_id, display_name=name)
    return Response(content=svg, media_type="image/svg+xml")
