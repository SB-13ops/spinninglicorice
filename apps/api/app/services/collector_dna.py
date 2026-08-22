from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    CollectionItem,
    CollectorAffinity,
    CollectorProfile,
    Release,
    ReleaseArtist,
    Artist,
)


CONDITION_RANK = {
    "M": 7,
    "NM": 6,
    "NM-": 6,
    "VG+": 5,
    "VG": 4,
    "G+": 3,
    "G": 2,
    "F": 1,
    "P": 0,
}


class CollectorDNAService:
    """Deterministic Collector DNA V1.

    This first version intentionally avoids LLM dependence. It infers simple,
    explainable preferences directly from imported collection data.
    """

    def __init__(self, db: Session):
        self.db = db

    def rebuild(self, *, user_id: UUID) -> dict[str, Any]:
        rows = self.db.execute(
            select(CollectionItem, Release)
            .join(Release, CollectionItem.release_id == Release.id)
            .where(CollectionItem.user_id == user_id)
        ).all()

        if not rows:
            return self._empty_result()

        years = [r.release_year for _, r in rows if r.release_year]
        prices = [
            Decimal(item.purchase_price)
            for item, _ in rows
            if item.purchase_price is not None
        ]
        conditions = [
            item.media_condition
            for item, _ in rows
            if item.media_condition
        ]

        artist_counts: Counter[str] = Counter()
        release_ids = [release.id for _, release in rows]
        if release_ids:
            artist_rows = self.db.execute(
                select(ReleaseArtist.release_id, Artist.name)
                .join(Artist, Artist.id == ReleaseArtist.artist_id)
                .where(ReleaseArtist.release_id.in_(release_ids))
            ).all()
            for _, artist_name in artist_rows:
                artist_counts[artist_name] += 1

        label_counts = Counter(
            release.label_name
            for _, release in rows
            if release.label_name
        )
        country_counts = Counter(
            release.country
            for _, release in rows
            if release.country
        )

        preferred_era_start = min(years) if years else None
        preferred_era_end = max(years) if years else None

        if prices:
            ordered = sorted(prices)
            low = ordered[max(0, int(len(ordered) * 0.25) - 1)]
            high = ordered[min(len(ordered) - 1, int(len(ordered) * 0.75))]
        else:
            low = None
            high = None

        preferred_condition = None
        if conditions:
            preferred_condition = max(
                Counter(conditions).items(),
                key=lambda x: (x[1], CONDITION_RANK.get(x[0], -1)),
            )[0]

        summary = {
            "record_count": len(rows),
            "top_artists": [
                {"name": name, "count": count}
                for name, count in artist_counts.most_common(10)
            ],
            "top_labels": [
                {"name": name, "count": count}
                for name, count in label_counts.most_common(8)
            ],
            "top_countries": [
                {"name": name, "count": count}
                for name, count in country_counts.most_common(5)
            ],
            "year_span": {
                "start": preferred_era_start,
                "end": preferred_era_end,
            },
        }

        profile = self.db.get(CollectorProfile, user_id)
        if profile is None:
            profile = CollectorProfile(user_id=user_id)
            self.db.add(profile)

        profile.preferred_era_start = preferred_era_start
        profile.preferred_era_end = preferred_era_end
        profile.typical_price_low = low
        profile.typical_price_high = high
        profile.preferred_condition = preferred_condition
        profile.pressing_preferences = {
            "countries": summary["top_countries"][:3],
            "labels": summary["top_labels"][:5],
        }
        profile.summary = summary

        self.db.query(CollectorAffinity).filter(
            CollectorAffinity.user_id == user_id
        ).delete(synchronize_session=False)

        total = max(len(rows), 1)

        for name, count in artist_counts.most_common(25):
            self.db.add(
                CollectorAffinity(
                    user_id=user_id,
                    affinity_type="artist",
                    affinity_key=name,
                    score=Decimal(str(round(count / total, 3))),
                    evidence={"collection_count": count},
                )
            )

        for name, count in label_counts.most_common(20):
            self.db.add(
                CollectorAffinity(
                    user_id=user_id,
                    affinity_type="label",
                    affinity_key=name,
                    score=Decimal(str(round(count / total, 3))),
                    evidence={"collection_count": count},
                )
            )

        self.db.commit()
        self.db.refresh(profile)

        return {
            "music_dna": {
                "top_artists": summary["top_artists"],
                "top_labels": summary["top_labels"],
                "year_span": summary["year_span"],
            },
            "collector_dna": {
                "typical_price_range": {
                    "low": float(low) if low is not None else None,
                    "high": float(high) if high is not None else None,
                },
                "preferred_condition": preferred_condition,
                "pressing_preferences": profile.pressing_preferences,
            },
            "record_count": len(rows),
        }

    def get(self, *, user_id: UUID) -> dict[str, Any]:
        profile = self.db.get(CollectorProfile, user_id)
        if profile is None:
            return self._empty_result()

        affinities = self.db.execute(
            select(CollectorAffinity)
            .where(CollectorAffinity.user_id == user_id)
            .order_by(CollectorAffinity.score.desc())
        ).scalars().all()

        top_artists = [
            {
                "name": a.affinity_key,
                "score": float(a.score),
                "count": a.evidence.get("collection_count"),
            }
            for a in affinities
            if a.affinity_type == "artist"
        ][:10]

        top_labels = [
            {
                "name": a.affinity_key,
                "score": float(a.score),
                "count": a.evidence.get("collection_count"),
            }
            for a in affinities
            if a.affinity_type == "label"
        ][:8]

        return {
            "music_dna": {
                "top_artists": top_artists,
                "top_labels": top_labels,
                "year_span": {
                    "start": profile.preferred_era_start,
                    "end": profile.preferred_era_end,
                },
            },
            "collector_dna": {
                "typical_price_range": {
                    "low": float(profile.typical_price_low) if profile.typical_price_low is not None else None,
                    "high": float(profile.typical_price_high) if profile.typical_price_high is not None else None,
                },
                "preferred_condition": profile.preferred_condition,
                "pressing_preferences": profile.pressing_preferences or {},
            },
            "record_count": (profile.summary or {}).get("record_count", 0),
        }

    @staticmethod
    def _empty_result() -> dict[str, Any]:
        return {
            "music_dna": {
                "top_artists": [],
                "top_labels": [],
                "year_span": {"start": None, "end": None},
            },
            "collector_dna": {
                "typical_price_range": {"low": None, "high": None},
                "preferred_condition": None,
                "pressing_preferences": {},
            },
            "record_count": 0,
        }
