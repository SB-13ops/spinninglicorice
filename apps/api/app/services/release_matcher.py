from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Artist, ExternalMapping, Release, ReleaseArtist


def _norm(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower()
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _similarity(a: str | None, b: str | None) -> float:
    aa, bb = _norm(a), _norm(b)
    if not aa or not bb:
        return 0.0
    return SequenceMatcher(None, aa, bb).ratio()


@dataclass
class ReleaseMatch:
    release_id: UUID
    confidence: int
    method: str
    breakdown: dict[str, int]


class ReleaseMatcher:
    """Matches a marketplace/catalog candidate to a Burnt Jacket release.

    Exact provider IDs always win. Fuzzy matching is only a fallback.
    """

    def __init__(self, db: Session):
        self.db = db

    def by_external_id(
        self,
        *,
        provider: str,
        external_release_id: str | int,
    ) -> ReleaseMatch | None:
        mapping = self.db.scalar(
            select(ExternalMapping).where(
                ExternalMapping.provider == provider,
                ExternalMapping.entity_type == "release",
                ExternalMapping.external_id == str(external_release_id),
            )
        )
        if not mapping:
            return None
        return ReleaseMatch(
            release_id=mapping.entity_id,
            confidence=100,
            method=f"{provider}_release_id",
            breakdown={"external_id": 100},
        )

    def fuzzy(
        self,
        *,
        title: str,
        artist: str | None = None,
        year: int | None = None,
        country: str | None = None,
        catalog_number: str | None = None,
    ) -> ReleaseMatch | None:
        candidates = self.db.execute(select(Release)).scalars().all()
        best: ReleaseMatch | None = None

        for release in candidates:
            title_score = round(_similarity(title, release.title) * 100)

            artist_score = 50
            if artist:
                names = self.db.execute(
                    select(Artist.name)
                    .join(ReleaseArtist, ReleaseArtist.artist_id == Artist.id)
                    .where(ReleaseArtist.release_id == release.id)
                ).scalars().all()
                artist_score = max(
                    [round(_similarity(artist, name) * 100) for name in names] or [0]
                )

            year_score = 50
            if year is not None and release.release_year is not None:
                delta = abs(year - release.release_year)
                year_score = 100 if delta == 0 else (70 if delta == 1 else 0)

            country_score = 50
            if country and release.country:
                country_score = 100 if _norm(country) == _norm(release.country) else 0

            cat_score = 50
            if catalog_number and release.catalog_number:
                cat_score = 100 if _norm(catalog_number) == _norm(release.catalog_number) else 0

            confidence = round(
                title_score * 0.40 +
                artist_score * 0.25 +
                year_score * 0.15 +
                cat_score * 0.15 +
                country_score * 0.05
            )

            match = ReleaseMatch(
                release_id=release.id,
                confidence=confidence,
                method="fuzzy_metadata",
                breakdown={
                    "title": title_score,
                    "artist": artist_score,
                    "year": year_score,
                    "catalog_number": cat_score,
                    "country": country_score,
                },
            )
            if best is None or match.confidence > best.confidence:
                best = match

        return best if best and best.confidence >= 72 else None
