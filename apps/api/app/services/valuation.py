"""Collection value tracking.

Values a collection from cached per-release valuations (falling back to what the
owner paid), captures point-in-time snapshots, and derives a worth-over-time
history plus best/worst movers by diffing snapshots.

Valuations come from Discogs price suggestions (cached in ReleaseValuation so we
don't re-fetch to value a whole collection). When a release has no market value
we fall back to the item's purchase price, and count how many items were
actually valued so the UI can be honest about coverage.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    CollectionItem,
    CollectionValueSnapshot,
    Release,
    ReleaseValuation,
)


def _release_values(db: Session, release_ids: list[uuid.UUID]) -> dict[str, float]:
    if not release_ids:
        return {}
    rows = db.execute(
        select(ReleaseValuation.release_id, ReleaseValuation.estimated_value).where(
            ReleaseValuation.release_id.in_(release_ids),
            ReleaseValuation.estimated_value.isnot(None),
        )
    ).all()
    return {str(rid): float(val) for rid, val in rows}


def compute_current_value(db: Session, user_id: uuid.UUID) -> dict:
    """Value the collection now. Returns totals + per-holding list (no writes)."""
    items = db.execute(
        select(CollectionItem, Release)
        .join(Release, CollectionItem.release_id == Release.id)
        .where(CollectionItem.user_id == user_id, CollectionItem.status == "collection")
    ).all()

    release_ids = [it.release_id for it, _ in items]
    values = _release_values(db, release_ids)

    holdings = []
    total = 0.0
    valued = 0
    for item, release in items:
        market = values.get(str(item.release_id))
        if market is not None:
            value = market
            valued += 1
        elif item.purchase_price is not None:
            value = float(item.purchase_price)
        else:
            value = None
        if value is not None:
            total += value
        holdings.append(
            {
                "release_id": str(item.release_id),
                "title": release.title,
                "value": round(value, 2) if value is not None else None,
            }
        )

    return {
        "total_value": round(total, 2),
        "item_count": len(items),
        "valued_count": valued,
        "holdings": holdings,
    }


def capture_snapshot(db: Session, user_id: uuid.UUID) -> CollectionValueSnapshot:
    """Compute and persist a snapshot of the collection's worth."""
    current = compute_current_value(db, user_id)
    snap = CollectionValueSnapshot(
        user_id=user_id,
        total_value=Decimal(str(current["total_value"])),
        item_count=current["item_count"],
        valued_count=current["valued_count"],
        holdings={"items": current["holdings"]},
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def get_value_summary(db: Session, user_id: uuid.UUID, *, movers_limit: int = 5) -> dict:
    """Current worth, history series, and best/worst movers vs the prior snapshot."""
    current = compute_current_value(db, user_id)

    snaps = db.scalars(
        select(CollectionValueSnapshot)
        .where(CollectionValueSnapshot.user_id == user_id)
        .order_by(CollectionValueSnapshot.captured_at.asc())
    ).all()

    history = [
        {"date": s.captured_at.date().isoformat(), "total": float(s.total_value)}
        for s in snaps
    ]

    # Change vs the most recent snapshot (if any).
    change_amount = change_pct = None
    if snaps:
        prev_total = float(snaps[-1].total_value)
        change_amount = round(current["total_value"] - prev_total, 2)
        if prev_total > 0:
            change_pct = round((change_amount / prev_total) * 100, 1)

    movers = _compute_movers(current["holdings"], snaps[-1] if snaps else None, movers_limit)

    return {
        "total_value": current["total_value"],
        "item_count": current["item_count"],
        "valued_count": current["valued_count"],
        "coverage_pct": round(100 * current["valued_count"] / current["item_count"], 0)
        if current["item_count"]
        else 0,
        "change_amount": change_amount,
        "change_pct": change_pct,
        "history": history,
        "best_movers": movers["best"],
        "worst_movers": movers["worst"],
    }


def _compute_movers(current_holdings: list[dict], prev_snap, limit: int) -> dict:
    if prev_snap is None:
        return {"best": [], "worst": []}
    prev = {
        h["release_id"]: h.get("value")
        for h in (prev_snap.holdings or {}).get("items", [])
        if h.get("value") is not None
    }
    deltas = []
    for h in current_holdings:
        rid = h["release_id"]
        now = h.get("value")
        was = prev.get(rid)
        if now is not None and was is not None and was != now:
            deltas.append(
                {
                    "release_id": rid,
                    "title": h["title"],
                    "change": round(now - was, 2),
                    "change_pct": round((now - was) / was * 100, 1) if was else None,
                    "value": now,
                }
            )
    deltas.sort(key=lambda d: d["change"], reverse=True)
    best = [d for d in deltas if d["change"] > 0][:limit]
    worst = [d for d in deltas if d["change"] < 0][-limit:]
    worst.sort(key=lambda d: d["change"])
    return {"best": best, "worst": worst}


def upsert_release_valuation(
    db: Session, release_id: uuid.UUID, value: float, *, source: str = "discogs"
) -> None:
    """Cache a release's current estimated value (called when we have Discogs
    price data, e.g. during a Hunter run or sync)."""
    row = db.get(ReleaseValuation, release_id)
    if row is None:
        row = ReleaseValuation(release_id=release_id, estimated_value=Decimal(str(value)), source=source)
        db.add(row)
    else:
        row.estimated_value = Decimal(str(value))
        row.source = source
    db.commit()
