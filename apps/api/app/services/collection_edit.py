"""Manually add, edit, and rate collection records.

Three ways a record gets in:
  1. Discogs sync (existing) — bulk import.
  2. Discogs search + pick (here) — find a release by text, import that exact
     release via the existing importer, and add it to the collection.
  3. By hand (here) — type title/artist/year; we create a lightweight
     Album/Release/Artist and a collection item with source="manual".

Plus editing any item's personal fields (rating, notes, condition, sleeve,
purchase price/date/location) regardless of how it got in.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import (
    Album,
    Artist,
    CollectionItem,
    ExternalAccount,
    ExternalMapping,
    Release,
    ReleaseArtist,
    WantlistItem,
)


# ---- editing personal fields (works for any item) --------------------------

_CONDITIONS = {
    "Mint (M)", "Near Mint (NM or M-)", "Very Good Plus (VG+)", "Very Good (VG)",
    "Good Plus (G+)", "Good (G)", "Fair (F)", "Poor (P)",
}


def update_item(
    db: Session,
    user_id: uuid.UUID,
    item_id: uuid.UUID,
    *,
    personal_rating: int | None = ...,
    personal_notes: str | None = ...,
    media_condition: str | None = ...,
    sleeve_condition: str | None = ...,
    purchase_price=...,
    purchase_date: date | None = ...,
    purchase_location: str | None = ...,
) -> CollectionItem | None:
    item = db.scalar(
        select(CollectionItem).where(
            CollectionItem.id == item_id, CollectionItem.user_id == user_id
        )
    )
    if item is None:
        return None

    # `...` sentinel = "not provided, leave as-is"; None = "clear it".
    if personal_rating is not ...:
        if personal_rating is not None and not (1 <= personal_rating <= 5):
            raise ValueError("Rating must be between 1 and 5.")
        item.personal_rating = personal_rating
    if personal_notes is not ...:
        item.personal_notes = personal_notes
    if media_condition is not ...:
        item.media_condition = media_condition
    if sleeve_condition is not ...:
        item.sleeve_condition = sleeve_condition
    if purchase_price is not ...:
        item.purchase_price = Decimal(str(purchase_price)) if purchase_price is not None else None
    if purchase_date is not ...:
        item.purchase_date = purchase_date
    if purchase_location is not ...:
        item.purchase_location = purchase_location

    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, user_id: uuid.UUID, item_id: uuid.UUID) -> bool:
    item = db.scalar(
        select(CollectionItem).where(
            CollectionItem.id == item_id, CollectionItem.user_id == user_id
        )
    )
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


# ---- add by hand -----------------------------------------------------------

def _next_copy_number(db: Session, user_id: uuid.UUID, release_id: uuid.UUID) -> int:
    n = db.scalar(
        select(func.max(CollectionItem.copy_number)).where(
            CollectionItem.user_id == user_id, CollectionItem.release_id == release_id
        )
    )
    return int(n or 0) + 1


def add_manual(
    db: Session,
    user_id: uuid.UUID,
    *,
    title: str,
    artist_name: str | None,
    year: int | None,
    label_name: str | None = None,
    catalog_number: str | None = None,
    country: str | None = None,
    image_url: str | None = None,
    media_condition: str | None = None,
    sleeve_condition: str | None = None,
    purchase_price=None,
    personal_rating: int | None = None,
    personal_notes: str | None = None,
    target: str = "collection",
    max_price=None,
):
    if personal_rating is not None and not (1 <= personal_rating <= 5):
        raise ValueError("Rating must be between 1 and 5.")
    if target not in ("collection", "wantlist"):
        raise ValueError("target must be 'collection' or 'wantlist'.")

    album = Album(title=title, release_year=year, album_type="album")
    db.add(album)
    db.flush()

    release = Release(
        album_id=album.id,
        title=title,
        release_year=year,
        label_name=label_name,
        catalog_number=catalog_number,
        country=country,
        image_url=image_url,
    )
    db.add(release)
    db.flush()

    if artist_name:
        artist = db.scalar(select(Artist).where(func.lower(Artist.name) == artist_name.lower()))
        if artist is None:
            artist = Artist(name=artist_name)
            db.add(artist)
            db.flush()
        db.add(ReleaseArtist(release_id=release.id, artist_id=artist.id, role="primary"))

    if target == "wantlist":
        item = WantlistItem(
            user_id=user_id,
            release_id=release.id,
            source="manual",
            max_price=Decimal(str(max_price)) if max_price is not None else None,
            minimum_media_condition=media_condition,
        )
    else:
        item = CollectionItem(
            user_id=user_id,
            release_id=release.id,
            copy_number=1,
            source="manual",
            media_condition=media_condition,
            sleeve_condition=sleeve_condition,
            purchase_price=Decimal(str(purchase_price)) if purchase_price is not None else None,
            personal_rating=personal_rating,
            personal_notes=personal_notes,
        )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ---- add from a Discogs release id (after searching) -----------------------

def search_discogs(db: Session, user_id: uuid.UUID, query: str, *, limit: int = 10) -> list[dict]:
    """Search Discogs for releases matching free text. Requires the user to have
    connected Discogs (uses their token). Returns lightweight candidates."""
    from app.services.discogs_client import client_for_account

    account = db.scalar(
        select(ExternalAccount).where(
            ExternalAccount.user_id == user_id, ExternalAccount.provider == "discogs"
        )
    )
    if account is None:
        raise RuntimeError("Connect your Discogs account first to search.")
    client = client_for_account(account)
    payload = client.database_search(query=query, per_page=min(limit, 25), page=1)
    out = []
    for row in payload.get("results", [])[:limit]:
        out.append(
            {
                "discogs_id": row.get("id"),
                "title": row.get("title"),
                "year": row.get("year"),
                "country": row.get("country"),
                "label": (row.get("label") or [None])[0] if isinstance(row.get("label"), list) else row.get("label"),
                "catno": row.get("catno"),
                "thumb": row.get("thumb") or row.get("cover_image"),
            }
        )
    return out


def search_discogs_by_barcode(db: Session, user_id: uuid.UUID, barcode: str, *, limit: int = 10) -> list[dict]:
    """Look up Discogs releases by a scanned barcode (UPC/EAN). Requires a
    connected Discogs account. Returns the same lightweight candidate shape as
    the text search so the frontend can reuse one 'pick a match' UI."""
    from app.services.discogs_client import client_for_account

    # Barcodes are digits; strip spaces/hyphens a scanner might include.
    cleaned = "".join(ch for ch in barcode if ch.isdigit())
    if len(cleaned) < 6:
        raise ValueError("That doesn't look like a barcode.")

    account = db.scalar(
        select(ExternalAccount).where(
            ExternalAccount.user_id == user_id, ExternalAccount.provider == "discogs"
        )
    )
    if account is None:
        raise RuntimeError("Connect your Discogs account first to scan.")
    client = client_for_account(account)
    payload = client.database_search(barcode=cleaned, per_page=min(limit, 25), page=1)
    out = []
    for row in payload.get("results", [])[:limit]:
        out.append(
            {
                "discogs_id": row.get("id"),
                "title": row.get("title"),
                "year": row.get("year"),
                "country": row.get("country"),
                "label": (row.get("label") or [None])[0] if isinstance(row.get("label"), list) else row.get("label"),
                "catno": row.get("catno"),
                "thumb": row.get("thumb") or row.get("cover_image"),
            }
        )
    return out


def add_from_discogs(db: Session, user_id: uuid.UUID, discogs_release_id: int | str, **personal) -> CollectionItem:
    """Import a specific Discogs release (reusing the sync importer) and add it."""
    from app.services.discogs_client import client_for_account
    from app.services.discogs_sync import DiscogsSyncService

    account = db.scalar(
        select(ExternalAccount).where(
            ExternalAccount.user_id == user_id, ExternalAccount.provider == "discogs"
        )
    )
    if account is None:
        raise RuntimeError("Connect your Discogs account first.")
    client = client_for_account(account)
    sync = DiscogsSyncService(db, client)
    release, _created = sync._get_or_import_release(discogs_release_id)
    db.flush()

    target = personal.get("target", "collection")
    if target not in ("collection", "wantlist"):
        raise ValueError("target must be 'collection' or 'wantlist'.")

    if target == "wantlist":
        # Wantlist is unique per (user, release) — return the existing row rather
        # than erroring if they add the same record twice.
        existing = db.scalar(
            select(WantlistItem).where(
                WantlistItem.user_id == user_id, WantlistItem.release_id == release.id
            )
        )
        if existing is not None:
            return existing
        mp = personal.get("max_price")
        item = WantlistItem(
            user_id=user_id,
            release_id=release.id,
            source="manual",
            max_price=Decimal(str(mp)) if mp is not None else None,
            minimum_media_condition=personal.get("media_condition"),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    copy_number = _next_copy_number(db, user_id, release.id)
    rating = personal.get("personal_rating")
    if rating is not None and not (1 <= rating <= 5):
        raise ValueError("Rating must be between 1 and 5.")
    pp = personal.get("purchase_price")
    item = CollectionItem(
        user_id=user_id,
        release_id=release.id,
        copy_number=copy_number,
        source="manual",
        media_condition=personal.get("media_condition"),
        sleeve_condition=personal.get("sleeve_condition"),
        purchase_price=Decimal(str(pp)) if pp is not None else None,
        personal_rating=rating,
        personal_notes=personal.get("personal_notes"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
