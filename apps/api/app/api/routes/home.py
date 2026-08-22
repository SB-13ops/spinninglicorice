from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_account_read
from app.db.deps import get_db
from app.models.core import (
    CollectionItem,
    Event,
    Hunt,
    HuntResult,
    MarketListing,
    Notification,
    ScoutRecommendation,
    User,
    WantlistItem,
)
from app.services.collector_dna import CollectorDNAService
from app.services.home_feature import resolve_home_feature

router = APIRouter(prefix="/home", tags=["home"])

def _build_home_feed(db: Session, owner_id) -> dict:
    """Build the home feed for an account. Shared by the authenticated route
    and the anonymous public read endpoint."""
    record_count = db.scalar(
        select(func.count()).select_from(CollectionItem).where(CollectionItem.user_id == owner_id)
    ) or 0
    wantlist_count = db.scalar(
        select(func.count()).select_from(WantlistItem).where(WantlistItem.user_id == owner_id)
    ) or 0

    dna = CollectorDNAService(db).get(user_id=owner_id)

    hunter_rows = db.execute(
        select(HuntResult, MarketListing, Hunt)
        .join(MarketListing, HuntResult.listing_id == MarketListing.id)
        .join(Hunt, HuntResult.hunt_id == Hunt.id)
        .where(Hunt.user_id == owner_id)
        .order_by(HuntResult.spinninglicorice_score.desc())
        .limit(4)
    ).all()

    hunter_found = []
    for result, listing, hunt in hunter_rows:
        market = (result.score_breakdown or {}).get("market", {})
        hunter_found.append({
            "hunt_name": hunt.name,
            "title": listing.title_raw,
            "price": float(listing.price),
            "score": result.spinninglicorice_score,
            "deal_label": result.deal_label,
            "explanation": result.explanation,
            "image_url": market.get("image_url"),
            "url": listing.listing_url,
            "owned": market.get("owned", False),
            "on_wantlist": market.get("on_wantlist", False),
        })

    scout_row = db.execute(
        select(ScoutRecommendation, Event)
        .join(Event, ScoutRecommendation.event_id == Event.id)
        .where(ScoutRecommendation.user_id == owner_id)
        .order_by(ScoutRecommendation.match_score.desc())
        .limit(1)
    ).first()

    concert_scout = None
    if scout_row:
        rec, event = scout_row
        concert_scout = {
            "name": event.name,
            "venue": event.venue_name,
            "city": event.city,
            "region": event.region,
            "starts_at": str(event.starts_at),
            "ticket_url": event.ticket_url,
            "match_score": rec.match_score,
            "reason": rec.reason,
        }

    notes = db.execute(
        select(Notification)
        .where(Notification.user_id == owner_id)
        .order_by(Notification.created_at.desc())
        .limit(5)
    ).scalars().all()

    return {
        "hero": resolve_home_feature(db, owner_id),
        "collection_snapshot": {
            "records": record_count,
            "wantlist": wantlist_count,
            "ai_picks": len(hunter_found),
        },
        "spinninglicorice_pick": hunter_found[0] if hunter_found else None,
        "hunter_found": hunter_found[1:],
        "recently_added": [],
        "collection_gaps": [],
        "collector_dna": dna,
        "concert_scout": concert_scout,
        "notifications": [
            {"title": n.title, "body": n.body, "type": n.notification_type}
            for n in notes
        ],
    }


@router.get("/feed")
def get_home_feed(
    ctx = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    return _build_home_feed(db, ctx.owner_id)
