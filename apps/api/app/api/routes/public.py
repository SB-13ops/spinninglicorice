"""Anonymous public read-only access.

These endpoints are NOT authenticated. Access is granted purely by possession of
a valid public-share token whose account has the link enabled (the owner's
privacy toggle). If the token is unknown or the link is disabled, every endpoint
returns 404 so a disabled/rotated link reveals nothing.

Only read views are exposed here (collection, collector DNA, home feed). There
is deliberately no public write path.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.core import AccountPublicShare
from app.services.collector_dna import CollectorDNAService

router = APIRouter(prefix="/public", tags=["public"])


def _resolve_owner_id(token: str, db: Session) -> uuid.UUID:
    share = db.scalar(select(AccountPublicShare).where(AccountPublicShare.token == token))
    if share is None or not share.enabled:
        # Same response whether the token never existed or the link is off.
        raise HTTPException(status_code=404, detail="This shared link is not available.")
    return share.owner_id


@router.get("/{token}/collection")
def public_collection(token: str, db: Session = Depends(get_db)):
    owner_id = _resolve_owner_id(token, db)
    from app.api.routes.collection import _serialize_collection  # lazy to avoid cycle

    return _serialize_collection(db, owner_id)


@router.get("/{token}/dna")
def public_dna(token: str, db: Session = Depends(get_db)):
    owner_id = _resolve_owner_id(token, db)
    return CollectorDNAService(db).get(user_id=owner_id)


@router.get("/{token}/home")
def public_home(token: str, db: Session = Depends(get_db)):
    owner_id = _resolve_owner_id(token, db)
    from app.api.routes.home import _build_home_feed  # lazy to avoid cycle

    return _build_home_feed(db, owner_id)
