"""Home-page personalization: the featured hero and its picker.

* GET  /home/feature        - resolved hero for the current account (read).
* PUT  /home/feature        - set the hero (album / artist / custom / default).
* GET  /home/feature/options - search the account's collection for albums and
                               artists to feature (powers the picker).

Reads use require_account_read; writing requires admin/owner via
require_account_write, so a read-only viewer can't change someone's home page.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.db.deps import get_db
from app.models.core import (
    Artist,
    CollectionItem,
    HomeFeature,
    Release,
    ReleaseArtist,
)
from app.schemas.home_feature import HomeFeatureUpdate, HomeHero
from app.services.home_feature import resolve_home_feature

router = APIRouter(prefix="/home/feature", tags=["home-feature"])


@router.get("", response_model=HomeHero)
def get_home_feature(
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    return resolve_home_feature(db, ctx.owner_id)


@router.put("", response_model=HomeHero)
def set_home_feature(
    payload: HomeFeatureUpdate,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    # Validate referenced ids belong to this account's collection.
    release_uuid = artist_uuid = None
    if payload.feature_type == "album":
        if not payload.release_id:
            raise HTTPException(status_code=400, detail="release_id is required for an album.")
        release_uuid = _parse_uuid(payload.release_id, "release_id")
        _assert_release_in_collection(db, ctx.owner_id, release_uuid)
    elif payload.feature_type == "artist":
        if not payload.artist_id:
            raise HTTPException(status_code=400, detail="artist_id is required for an artist.")
        artist_uuid = _parse_uuid(payload.artist_id, "artist_id")
        _assert_artist_in_collection(db, ctx.owner_id, artist_uuid)

    feature = db.get(HomeFeature, ctx.owner_id)
    if feature is None:
        feature = HomeFeature(owner_id=ctx.owner_id)
        db.add(feature)

    feature.feature_type = payload.feature_type
    feature.release_id = release_uuid
    feature.artist_id = artist_uuid
    feature.custom_image_url = payload.custom_image_url if payload.feature_type == "custom" else None
    feature.custom_title = payload.custom_title if payload.feature_type == "custom" else None
    feature.custom_subtitle = payload.custom_subtitle if payload.feature_type == "custom" else None
    db.commit()

    return resolve_home_feature(db, ctx.owner_id)


@router.get("/options")
def feature_options(
    q: str | None = Query(default=None),
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    """Albums and artists from the account's collection, for the picker."""
    like = f"%{q}%" if q else None

    album_stmt = (
        select(Release.id, Release.title, Release.image_url)
        .join(CollectionItem, CollectionItem.release_id == Release.id)
        .where(CollectionItem.user_id == ctx.owner_id)
    )
    if like:
        album_stmt = album_stmt.where(Release.title.ilike(like))
    albums = [
        {"release_id": str(rid), "title": title, "image_url": img}
        for rid, title, img in db.execute(album_stmt.order_by(Release.title).limit(25)).all()
    ]

    artist_stmt = (
        select(distinct(Artist.id), Artist.name)
        .join(ReleaseArtist, ReleaseArtist.artist_id == Artist.id)
        .join(CollectionItem, CollectionItem.release_id == ReleaseArtist.release_id)
        .where(CollectionItem.user_id == ctx.owner_id)
    )
    if like:
        artist_stmt = artist_stmt.where(Artist.name.ilike(like))
    artists = [
        {"artist_id": str(aid), "name": name}
        for aid, name in db.execute(artist_stmt.order_by(Artist.name).limit(25)).all()
    ]

    return {"albums": albums, "artists": artists}


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field}.")


def _assert_release_in_collection(db: Session, owner_id: uuid.UUID, release_id: uuid.UUID) -> None:
    exists = db.scalar(
        select(CollectionItem.id).where(
            CollectionItem.user_id == owner_id, CollectionItem.release_id == release_id
        )
    )
    if not exists:
        raise HTTPException(status_code=404, detail="That release isn't in this collection.")


def _assert_artist_in_collection(db: Session, owner_id: uuid.UUID, artist_id: uuid.UUID) -> None:
    exists = db.scalar(
        select(CollectionItem.id)
        .join(ReleaseArtist, ReleaseArtist.release_id == CollectionItem.release_id)
        .where(CollectionItem.user_id == owner_id, ReleaseArtist.artist_id == artist_id)
        .limit(1)
    )
    if not exists:
        raise HTTPException(status_code=404, detail="That artist isn't in this collection.")
