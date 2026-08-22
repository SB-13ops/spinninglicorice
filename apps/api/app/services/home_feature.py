"""Resolve an account's home personalization into a display-ready hero.

Turns a HomeFeature row (album / artist / custom / default) into a consistent
payload the web app renders as a themed full-background banner:

    {
      "type": "album" | "artist" | "custom" | "default",
      "title": str,
      "subtitle": str | None,
      "image_url": str | None,   # backdrop + cover art
      "ref_id": str | None,      # release_id or artist_id, for linking
    }
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    Artist,
    HomeFeature,
    Release,
    ReleaseArtist,
)

DEFAULT_HERO = {
    "type": "default",
    "title": "Your collection. Your hunt. Your music.",
    "subtitle": "Personalize this space with a favorite record or artist.",
    "image_url": None,
    "ref_id": None,
}


def _release_artists(db: Session, release_id: uuid.UUID) -> list[str]:
    return list(
        db.scalars(
            select(Artist.name)
            .join(ReleaseArtist, ReleaseArtist.artist_id == Artist.id)
            .where(ReleaseArtist.release_id == release_id)
        ).all()
    )


def resolve_home_feature(db: Session, owner_id: uuid.UUID) -> dict:
    feature = db.get(HomeFeature, owner_id)
    if feature is None or feature.feature_type == "default":
        return dict(DEFAULT_HERO)

    if feature.feature_type == "album" and feature.release_id:
        release = db.get(Release, feature.release_id)
        if release is not None:
            artists = _release_artists(db, release.id)
            return {
                "type": "album",
                "title": release.title,
                "subtitle": ", ".join(artists) if artists else None,
                "image_url": release.image_url,
                "ref_id": str(release.id),
            }

    if feature.feature_type == "artist" and feature.artist_id:
        artist = db.get(Artist, feature.artist_id)
        if artist is not None:
            # Use a representative cover from the artist's releases as backdrop.
            image = db.scalar(
                select(Release.image_url)
                .join(ReleaseArtist, ReleaseArtist.release_id == Release.id)
                .where(ReleaseArtist.artist_id == artist.id, Release.image_url.isnot(None))
                .limit(1)
            )
            return {
                "type": "artist",
                "title": artist.name,
                "subtitle": "Featured artist",
                "image_url": image,
                "ref_id": str(artist.id),
            }

    if feature.feature_type == "custom":
        return {
            "type": "custom",
            "title": feature.custom_title or "Featured",
            "subtitle": feature.custom_subtitle,
            "image_url": feature.custom_image_url,
            "ref_id": None,
        }

    # Referenced record/artist was deleted, or an unknown type -> default.
    return dict(DEFAULT_HERO)
