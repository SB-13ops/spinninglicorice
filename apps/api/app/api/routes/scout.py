from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.db.deps import get_db
from app.models.core import Event, ScoutRecommendation, User
from app.services.scout_service import ScoutService

router = APIRouter(prefix="/scout", tags=["scout"])

def _owner(db, owner_id):
    return db.get(User, owner_id)



@router.post("/refresh")
def refresh_scout(
    ctx = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    items = ScoutService(db, _owner(db, ctx.owner_id)).build_recommendations(limit=20)
    return {"items": items, "count": len(items)}


@router.get("/recommendations")
def get_scout_recommendations(
    ctx = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(ScoutRecommendation, Event)
        .join(Event, ScoutRecommendation.event_id == Event.id)
        .where(ScoutRecommendation.user_id == ctx.owner_id)
        .order_by(ScoutRecommendation.match_score.desc())
        .limit(20)
    ).all()

    from app.services.affiliate_links import ticket_link

    return {
        "items": [
            {
                "recommendation_id": str(rec.id),
                "event_id": str(event.id),
                "name": event.name,
                "venue": event.venue_name,
                "city": event.city,
                "region": event.region,
                "starts_at": str(event.starts_at),
                "ticket_url": event.ticket_url,
                "ticket_link": ticket_link(event.name, event.city, event.ticket_url),
                "match_score": rec.match_score,
                "reason": rec.reason,
                "evidence": rec.evidence,
            }
            for rec, event in rows
        ]
    }
