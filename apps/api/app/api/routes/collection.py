from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.db.deps import get_db
from app.models.core import Artist, CollectionItem, Release, ReleaseArtist
from app.services.collection_edit import (
    add_from_discogs,
    add_manual,
    remove_item,
    search_discogs,
    search_discogs_by_barcode,
    update_item,
)

router = APIRouter(prefix="/collection", tags=["collection"])


def _serialize_collection(
    db: Session,
    owner_id: uuid.UUID,
    q: str | None = None,
    year: int | None = None,
    country: str | None = None,
) -> dict:
    """Build the collection payload for an account. Shared by the authenticated
    route and the anonymous public read endpoint."""
    stmt = (
        select(CollectionItem, Release)
        .join(Release, CollectionItem.release_id == Release.id)
        .where(CollectionItem.user_id == owner_id)
    )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Release.title.ilike(like),
                Release.label_name.ilike(like),
                Release.catalog_number.ilike(like),
            )
        )
    if year:
        stmt = stmt.where(Release.release_year == year)
    if country:
        stmt = stmt.where(Release.country == country)

    rows = db.execute(stmt.order_by(Release.title)).all()

    release_ids = [release.id for _, release in rows]
    artist_map: dict[str, list[str]] = {}
    if release_ids:
        artist_rows = db.execute(
            select(ReleaseArtist.release_id, Artist.name)
            .join(Artist, Artist.id == ReleaseArtist.artist_id)
            .where(ReleaseArtist.release_id.in_(release_ids))
        ).all()
        for release_id, artist_name in artist_rows:
            artist_map.setdefault(str(release_id), []).append(artist_name)

    items = [
        {
            "collection_item_id": str(item.id),
            "release_id": str(release.id),
            "title": release.title,
            "artists": artist_map.get(str(release.id), []),
            "year": release.release_year,
            "country": release.country,
            "catalog_number": release.catalog_number,
            "label": release.label_name,
            "pressing": release.pressing_text,
            "image_url": release.image_url,
            "media_condition": item.media_condition,
            "sleeve_condition": item.sleeve_condition,
            "purchase_price": float(item.purchase_price) if item.purchase_price is not None else None,
            "personal_rating": item.personal_rating,
            "personal_notes": item.personal_notes,
            "source": item.source,
        }
        for item, release in rows
    ]

    return {
        "items": items,
        "summary": {
            "records": len(items),
            "years": sorted({x["year"] for x in items if x["year"]}),
            "countries": sorted({x["country"] for x in items if x["country"]}),
        },
    }


@router.get("")
def list_collection(
    q: str | None = Query(default=None),
    year: int | None = Query(default=None),
    country: str | None = Query(default=None),
    ctx = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    return _serialize_collection(db, ctx.owner_id, q=q, year=year, country=country)


# --------------------------------------------------------------------------
# Adding, editing, and rating records
# --------------------------------------------------------------------------

class ManualAdd(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    artist_name: str | None = Field(default=None, max_length=300)
    year: int | None = Field(default=None, ge=1900, le=2100)
    label_name: str | None = None
    catalog_number: str | None = None
    country: str | None = None
    image_url: str | None = None
    media_condition: str | None = None
    sleeve_condition: str | None = None
    purchase_price: float | None = Field(default=None, ge=0)
    personal_rating: int | None = Field(default=None, ge=1, le=5)
    personal_notes: str | None = None
    target: str = Field(default="collection", pattern="^(collection|wantlist)$")
    max_price: float | None = Field(default=None, ge=0)


class DiscogsAdd(BaseModel):
    discogs_release_id: int
    media_condition: str | None = None
    sleeve_condition: str | None = None
    purchase_price: float | None = Field(default=None, ge=0)
    personal_rating: int | None = Field(default=None, ge=1, le=5)
    personal_notes: str | None = None
    target: str = Field(default="collection", pattern="^(collection|wantlist)$")
    max_price: float | None = Field(default=None, ge=0)


class ItemEdit(BaseModel):
    # Only fields present are changed; use JSON null to clear a field.
    personal_rating: int | None = Field(default=None, ge=1, le=5)
    personal_notes: str | None = None
    media_condition: str | None = None
    sleeve_condition: str | None = None
    purchase_price: float | None = Field(default=None, ge=0)
    purchase_location: str | None = None

    model_config = {"extra": "forbid"}


@router.post("", status_code=201)
def add_record(
    payload: ManualAdd,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    """Add a record by hand (type in the details)."""
    try:
        item = add_manual(db, ctx.owner_id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": str(item.id), "release_id": str(item.release_id), "target": payload.target}


@router.get("/search")
def search_records(
    q: str = Query(min_length=1),
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    """Search Discogs for a release to add (requires a connected Discogs account)."""
    try:
        return {"results": search_discogs(db, ctx.owner_id, q)}
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/scan")
def scan_barcode(
    barcode: str = Query(min_length=6, max_length=32),
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    """Look up a scanned barcode (UPC/EAN) on Discogs and return candidate
    releases to add. Same result shape as /collection/search."""
    try:
        return {"results": search_discogs_by_barcode(db, ctx.owner_id, barcode)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/from-discogs", status_code=201)
def add_from_discogs_route(
    payload: DiscogsAdd,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    """Add a specific Discogs release (chosen from search) to the collection."""
    try:
        item = add_from_discogs(db, ctx.owner_id, payload.discogs_release_id,
                                **payload.model_dump(exclude={"discogs_release_id"}))
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"id": str(item.id), "release_id": str(item.release_id), "target": payload.target}


@router.patch("/{item_id}")
def edit_record(
    item_id: str,
    payload: ItemEdit,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    """Edit or rate a record (any field left out is unchanged)."""
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item id.")
    # Only pass through fields the client actually sent, so omitted != clear.
    sent = payload.model_dump(exclude_unset=True)
    try:
        item = update_item(db, ctx.owner_id, iid, **sent)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if item is None:
        raise HTTPException(status_code=404, detail="Record not found.")
    return {
        "id": str(item.id),
        "personal_rating": item.personal_rating,
        "personal_notes": item.personal_notes,
        "media_condition": item.media_condition,
        "sleeve_condition": item.sleeve_condition,
        "purchase_price": float(item.purchase_price) if item.purchase_price is not None else None,
        "purchase_location": item.purchase_location,
    }


@router.delete("/{item_id}", status_code=204)
def delete_record(
    item_id: str,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid item id.")
    if not remove_item(db, ctx.owner_id, iid):
        raise HTTPException(status_code=404, detail="Record not found.")
    return None
