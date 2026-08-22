"""Complete-the-collection: find releases by artists you collect that you don't
own yet.

Approach: for each artist you already own records by (ranked by how many you
own), look at that artist's releases known to Burnt Jacket and surface the ones
missing from your collection. This turns the collection into a to-hunt list.

The universe of "their releases" is what's in our DB (imported via Discogs sync
and prior hunts). A future enhancement can pull an artist's full Discogs
discography to widen the net; the shape here stays the same.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import (
    Artist,
    CollectionItem,
    Release,
    ReleaseArtist,
)


def artist_completion(db: Session, user_id: uuid.UUID, *, max_artists: int = 8) -> list[dict]:
    """For the user's most-collected artists, report owned vs. known and list
    the missing releases."""
    # Releases the user owns, with their artists.
    owned_release_ids = set(
        str(r) for r in db.scalars(
            select(CollectionItem.release_id).where(
                CollectionItem.user_id == user_id,
                CollectionItem.status == "collection",
            )
        ).all()
    )
    if not owned_release_ids:
        return []

    # Rank artists by how many of their releases the user owns.
    artist_counts = db.execute(
        select(Artist.id, Artist.name, func.count(func.distinct(ReleaseArtist.release_id)))
        .join(ReleaseArtist, ReleaseArtist.artist_id == Artist.id)
        .join(CollectionItem, CollectionItem.release_id == ReleaseArtist.release_id)
        .where(CollectionItem.user_id == user_id, CollectionItem.status == "collection")
        .group_by(Artist.id, Artist.name)
        .order_by(func.count(func.distinct(ReleaseArtist.release_id)).desc())
        .limit(max_artists)
    ).all()

    results = []
    for artist_id, artist_name, owned_count in artist_counts:
        # All releases by this artist known to Burnt Jacket.
        known = db.execute(
            select(Release.id, Release.title, Release.release_year, Release.image_url)
            .join(ReleaseArtist, ReleaseArtist.release_id == Release.id)
            .where(ReleaseArtist.artist_id == artist_id)
            .order_by(Release.release_year.asc().nulls_last())
        ).all()

        missing = [
            {
                "release_id": str(rid),
                "title": title,
                "year": year,
                "image_url": img,
            }
            for rid, title, year, img in known
            if str(rid) not in owned_release_ids
        ]
        known_count = len(known)
        if known_count == 0:
            continue
        results.append(
            {
                "artist_id": str(artist_id),
                "artist": artist_name,
                "owned": owned_count,
                "known": known_count,
                "missing_count": len(missing),
                "completion_pct": round(100 * owned_count / known_count),
                "missing": missing[:20],
            }
        )
    return results
