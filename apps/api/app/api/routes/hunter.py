from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.db.deps import get_db
from app.models.core import ExternalAccount, Hunt, HuntCriteria, HuntResult, MarketListing, User
from app.schemas.hunter import HuntCreate, HuntParseRequest, HuntUpdate
from app.services.demo_marketplace import search_demo
from app.services.discogs_hunter_provider import DiscogsHunterProvider
from app.services.ai.hunt_parser_ai import parse_hunt_query_smart as parse_hunt_query
from app.services.hunter_score import ScoreInput, calculate_spinninglicorice_score

router = APIRouter(prefix="/hunter", tags=["hunter"])

def _serialize_hunt(hunt: Hunt, criteria: HuntCriteria | None) -> dict:
    return {
        "id": str(hunt.id),
        "name": hunt.name,
        "query": hunt.natural_language_query,
        "auto_hunt": hunt.is_auto,
        "active": hunt.is_active,
        "criteria": criteria.criteria if criteria else {},
        "created_at": hunt.created_at,
    }

@router.post("/parse")
def parse_hunt(request: HuntParseRequest):
    return {"query": request.query, "criteria": parse_hunt_query(request.query)}

@router.get("/hunts")
def list_hunts(ctx = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    hunts = db.execute(
        select(Hunt).where(Hunt.user_id == ctx.owner_id).order_by(Hunt.created_at.desc())
    ).scalars().all()
    return {"items": [_serialize_hunt(h, db.get(HuntCriteria, h.id)) for h in hunts]}

@router.post("/hunts")
def create_hunt(payload: HuntCreate, ctx = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    hunt = Hunt(
        user_id=ctx.owner_id,
        name=payload.name,
        natural_language_query=payload.query,
        is_auto=payload.auto_hunt,
        is_active=True,
    )
    db.add(hunt)
    db.flush()
    criteria = HuntCriteria(hunt_id=hunt.id, criteria=parse_hunt_query(payload.query))
    db.add(criteria)
    db.commit()
    db.refresh(hunt)
    return _serialize_hunt(hunt, criteria)

@router.patch("/hunts/{hunt_id}")
def update_hunt(hunt_id: UUID, payload: HuntUpdate, ctx = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    hunt = db.get(Hunt, hunt_id)
    if not hunt or hunt.user_id != ctx.owner_id:
        raise HTTPException(status_code=404, detail="Hunt not found.")

    if payload.name is not None:
        hunt.name = payload.name
    if payload.auto_hunt is not None:
        hunt.is_auto = payload.auto_hunt
    if payload.active is not None:
        hunt.is_active = payload.active

    criteria = db.get(HuntCriteria, hunt.id)
    if payload.query is not None:
        hunt.natural_language_query = payload.query
        parsed = parse_hunt_query(payload.query)
        if criteria is None:
            criteria = HuntCriteria(hunt_id=hunt.id, criteria=parsed)
            db.add(criteria)
        else:
            criteria.criteria = parsed

    db.commit()
    db.refresh(hunt)
    return _serialize_hunt(hunt, criteria)

@router.delete("/hunts/{hunt_id}")
def delete_hunt(hunt_id: UUID, ctx = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    hunt = db.get(Hunt, hunt_id)
    if not hunt or hunt.user_id != ctx.owner_id:
        raise HTTPException(status_code=404, detail="Hunt not found.")
    db.query(HuntResult).filter(HuntResult.hunt_id == hunt.id).delete(synchronize_session=False)
    criteria = db.get(HuntCriteria, hunt.id)
    if criteria:
        db.delete(criteria)
    db.delete(hunt)
    db.commit()
    return {"deleted": True}


@router.post("/hunts/{hunt_id}/refresh")
def refresh_hunt(hunt_id: UUID, ctx = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    hunt = db.get(Hunt, hunt_id)
    if not hunt or hunt.user_id != ctx.owner_id:
        raise HTTPException(status_code=404, detail="Hunt not found.")

    criteria_row = db.get(HuntCriteria, hunt.id)
    criteria = criteria_row.criteria if criteria_row else {}

    previous = db.execute(
        select(HuntResult).where(HuntResult.hunt_id == hunt.id)
    ).scalars().all()
    for result in previous:
        listing = db.get(MarketListing, result.listing_id)
        db.delete(result)
        if listing and listing.source in {"demo", "discogs_market"}:
            db.delete(listing)
    db.flush()

    discogs_account = db.scalar(
        select(ExternalAccount).where(
            ExternalAccount.user_id == ctx.owner_id,
            ExternalAccount.provider == "discogs",
        )
    )

    created = []

    # Prefer the real Discogs provider whenever a user has connected Discogs.
    if discogs_account:
        try:
            opportunities = DiscogsHunterProvider(db, user=user).search(criteria, limit=12)
        except Exception as exc:
            opportunities = []
            provider_error = str(exc)
        else:
            provider_error = None

        for opp in opportunities:
            # Discogs returns a real release-level marketplace floor and count.
            # This is a market opportunity, not a claim about one specific seller.
            if opp.current_lowest_price is None:
                continue

            listing = MarketListing(
                source="discogs_market",
                external_listing_id=f"release-{opp.discogs_release_id}",
                release_id=opp.spinninglicorice_release_id,
                title_raw=f"{opp.artist} — {opp.title}",
                price=opp.current_lowest_price,
                shipping=None,
                media_condition=opp.media_condition_basis,
                sleeve_condition=None,
                seller_name="Discogs Marketplace",
                listing_url=opp.marketplace_url,
            )
            db.add(listing)
            db.flush()

            collector_match = 92 if opp.on_wantlist else 82
            listing_confidence = 92 if opp.num_for_sale >= 5 else (82 if opp.num_for_sale >= 2 else 70)

            score_data = calculate_spinninglicorice_score(
                ScoreInput(
                    asking_price=opp.current_lowest_price,
                    estimated_low=opp.estimated_low,
                    estimated_high=opp.estimated_high,
                    owned=opp.owned,
                    on_wantlist=opp.on_wantlist,
                    collector_match=collector_match,
                    media_condition=None,
                    pressing_match=100,  # exact Discogs release ID → SpinningLicorice release
                    listing_confidence=listing_confidence,
                )
            )

            ownership_text = "YOU OWN THIS PRESSING" if opp.owned else "NOT IN COLLECTION"
            if opp.on_wantlist:
                ownership_text = "ON YOUR WANTLIST"

            value_text = (
                f"estimated ${opp.estimated_low:.0f}–${opp.estimated_high:.0f}"
                if opp.estimated_low is not None and opp.estimated_high is not None
                else "market estimate unavailable"
            )
            explanation = (
                f"{score_data['deal_label']}: Discogs lowest ${opp.current_lowest_price:.0f} · "
                f"{value_text} · {ownership_text} · "
                f"{opp.num_for_sale} for sale"
            )

            breakdown = dict(score_data["breakdown"])
            breakdown["market"] = {
                "provider": "discogs",
                "discogs_release_id": opp.discogs_release_id,
                "num_for_sale": opp.num_for_sale,
                "estimated_low": opp.estimated_low,
                "estimated_high": opp.estimated_high,
                "owned": opp.owned,
                "on_wantlist": opp.on_wantlist,
                "match_confidence": 100,
                "match_method": "discogs_release_id",
                "image_url": opp.image_url,
                "year": opp.year,
                "country": opp.country,
            }

            result = HuntResult(
                hunt_id=hunt.id,
                listing_id=listing.id,
                spinninglicorice_score=score_data["score"],
                deal_label=score_data["deal_label"],
                score_breakdown=breakdown,
                explanation=explanation,
            )
            db.add(result)
            db.flush()

            created.append({
                "result_id": str(result.id),
                "listing_id": str(listing.id),
                "source": "discogs",
                "release_id": str(opp.spinninglicorice_release_id),
                "discogs_release_id": opp.discogs_release_id,
                "title": listing.title_raw,
                "price": opp.current_lowest_price,
                "shipping": None,
                "condition": opp.media_condition_basis,
                "estimated_value_low": opp.estimated_low,
                "estimated_value_high": opp.estimated_high,
                "num_for_sale": opp.num_for_sale,
                "owned": opp.owned,
                "on_wantlist": opp.on_wantlist,
                "match_confidence": 100,
                "score": score_data["score"],
                "deal_label": score_data["deal_label"],
                "explanation": explanation,
                "seller": "Discogs Marketplace",
                "image_url": opp.image_url,
                "url": opp.marketplace_url,
            })

        if created:
            db.commit()
            created.sort(key=lambda x: x["score"], reverse=True)
            return {
                "hunt_id": str(hunt.id),
                "provider": "discogs",
                "results": created,
            }

    # Development fallback keeps Hunter usable before Discogs is connected
    # or when no real Discogs opportunities match.
    matches = search_demo(criteria)
    for demo in matches:
        listing = MarketListing(
            source="demo",
            external_listing_id=f"{hunt.id}-{demo.external_listing_id}",
            release_id=None,
            title_raw=demo.title_raw,
            price=demo.price,
            shipping=demo.shipping,
            media_condition=demo.media_condition,
            sleeve_condition=demo.sleeve_condition,
            seller_name=demo.seller_name,
            listing_url=demo.listing_url,
        )
        db.add(listing)
        db.flush()

        score_data = calculate_spinninglicorice_score(
            ScoreInput(
                asking_price=demo.price,
                estimated_low=demo.estimated_low,
                estimated_high=demo.estimated_high,
                owned=False,
                on_wantlist=False,
                collector_match=82 if demo.artist.lower().startswith("grateful dead") else 78,
                media_condition=demo.media_condition,
                pressing_match=80 if demo.country == "US" else 60,
                listing_confidence=75,
            )
        )

        explanation = (
            f"{score_data['deal_label']}: asking ${demo.price:.0f} · "
            f"typical ${demo.estimated_low:.0f}–${demo.estimated_high:.0f} · "
            f"{demo.media_condition} condition"
        )
        breakdown = dict(score_data["breakdown"])
        breakdown["market"] = {
            "provider": "demo",
            "estimated_low": demo.estimated_low,
            "estimated_high": demo.estimated_high,
            "owned": False,
            "on_wantlist": False,
            "match_confidence": 0,
        }

        result = HuntResult(
            hunt_id=hunt.id,
            listing_id=listing.id,
            spinninglicorice_score=score_data["score"],
            deal_label=score_data["deal_label"],
            score_breakdown=breakdown,
            explanation=explanation,
        )
        db.add(result)
        db.flush()

        created.append({
            "result_id": str(result.id),
            "listing_id": str(listing.id),
            "source": "demo",
            "title": demo.title_raw,
            "price": demo.price,
            "shipping": demo.shipping,
            "condition": demo.media_condition,
            "estimated_value_low": demo.estimated_low,
            "estimated_value_high": demo.estimated_high,
            "num_for_sale": None,
            "owned": False,
            "on_wantlist": False,
            "match_confidence": 0,
            "score": score_data["score"],
            "deal_label": score_data["deal_label"],
            "explanation": explanation,
            "seller": demo.seller_name,
            "image_url": None,
            "url": demo.listing_url,
        })

    db.commit()
    created.sort(key=lambda x: x["score"], reverse=True)
    return {
        "hunt_id": str(hunt.id),
        "provider": "demo",
        "provider_note": (
            "Connect Discogs for real marketplace data."
            if not discogs_account
            else "No matching Discogs marketplace opportunities were returned; showing demo results."
        ),
        "results": created,
    }



@router.get("/hunts/{hunt_id}/results")
def hunt_results(hunt_id: UUID, ctx = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    hunt = db.get(Hunt, hunt_id)
    if not hunt or hunt.user_id != ctx.owner_id:
        raise HTTPException(status_code=404, detail="Hunt not found.")

    rows = db.execute(
        select(HuntResult, MarketListing)
        .join(MarketListing, HuntResult.listing_id == MarketListing.id)
        .where(HuntResult.hunt_id == hunt.id)
        .order_by(HuntResult.spinninglicorice_score.desc())
    ).all()

    items = []
    for result, listing in rows:
        market = (result.score_breakdown or {}).get("market", {})
        items.append({
            "result_id": str(result.id),
            "listing_id": str(listing.id),
            "source": market.get("provider") or listing.source,
            "release_id": str(listing.release_id) if listing.release_id else None,
            "discogs_release_id": market.get("discogs_release_id"),
            "title": listing.title_raw,
            "price": float(listing.price),
            "shipping": float(listing.shipping) if listing.shipping is not None else None,
            "condition": listing.media_condition,
            "estimated_value_low": market.get("estimated_low"),
            "estimated_value_high": market.get("estimated_high"),
            "num_for_sale": market.get("num_for_sale"),
            "owned": market.get("owned", False),
            "on_wantlist": market.get("on_wantlist", False),
            "match_confidence": market.get("match_confidence"),
            "image_url": market.get("image_url"),
            "score": result.spinninglicorice_score,
            "deal_label": result.deal_label,
            "score_breakdown": result.score_breakdown,
            "explanation": result.explanation,
            "seller": listing.seller_name,
            "url": listing.listing_url,
        })

    return {"items": items}
