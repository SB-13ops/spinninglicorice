from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    Album,
    Artist,
    CollectionItem,
    ExternalMapping,
    Release,
    ReleaseArtist,
    WantlistItem,
)
from app.services.discogs_client import DiscogsClient
from app.services.discogs_normalizer import normalize_release_payload


class DiscogsSyncService:
    def __init__(self, db: Session, client: DiscogsClient):
        self.db = db
        self.client = client

    def sync_collection_and_wantlist(self, *, user_id: UUID, username: str) -> dict[str, int]:
        stats = {
            "collection_seen": 0,
            "collection_added": 0,
            "wantlist_seen": 0,
            "wantlist_added": 0,
            "catalog_releases_created": 0,
        }

        for collection_row in self.client.iter_collection(username):
            stats["collection_seen"] += 1
            release_id = collection_row.get("id")
            if release_id is None:
                continue

            release, created = self._get_or_import_release(release_id)
            stats["catalog_releases_created"] += int(created)

            instance_id = collection_row.get("instance_id") or 1
            existing = self.db.scalar(
                select(CollectionItem).where(
                    CollectionItem.user_id == user_id,
                    CollectionItem.release_id == release.id,
                    CollectionItem.copy_number == int(instance_id),
                )
            )
            if not existing:
                self.db.add(
                    CollectionItem(
                        user_id=user_id,
                        release_id=release.id,
                        copy_number=int(instance_id),
                        source="discogs",
                    )
                )
                stats["collection_added"] += 1

        for want_row in self.client.iter_wantlist(username):
            stats["wantlist_seen"] += 1
            release_id = want_row.get("id")
            if release_id is None:
                continue

            release, created = self._get_or_import_release(release_id)
            stats["catalog_releases_created"] += int(created)

            existing = self.db.scalar(
                select(WantlistItem).where(
                    WantlistItem.user_id == user_id,
                    WantlistItem.release_id == release.id,
                )
            )
            if not existing:
                self.db.add(
                    WantlistItem(
                        user_id=user_id,
                        release_id=release.id,
                        source="discogs",
                    )
                )
                stats["wantlist_added"] += 1

        self.db.commit()
        return stats

    def _get_or_import_release(self, discogs_release_id: int | str) -> tuple[Release, bool]:
        release, _created, _raw = self._get_or_import_release_with_payload(discogs_release_id)
        return release, _created

    def _get_or_import_release_with_payload(
        self, discogs_release_id: int | str
    ) -> tuple[Release, bool, dict | None]:
        """Like _get_or_import_release, but also returns the raw Discogs release
        payload when a fetch happened (None on a cache hit from our DB).

        Callers that need the payload (e.g. the Hunter provider) can reuse it
        instead of calling client.release() a second time. On the DB-hit path
        the payload is None; client.release() is itself response-cached, so the
        follow-up call is cheap.
        """
        mapping = self.db.scalar(
            select(ExternalMapping).where(
                ExternalMapping.provider == "discogs",
                ExternalMapping.entity_type == "release",
                ExternalMapping.external_id == str(discogs_release_id),
            )
        )
        if mapping:
            release = self.db.get(Release, mapping.entity_id)
            if release:
                return release, False, None

        raw = self.client.release(discogs_release_id)
        data = normalize_release_payload(raw)

        album = Album(
            title=data["title"],
            release_year=data["release_year"],
            album_type="album",
        )
        self.db.add(album)
        self.db.flush()

        release = Release(
            album_id=album.id,
            title=data["title"],
            country=data["country"],
            release_year=data["release_year"],
            catalog_number=data["catalog_number"],
            label_name=data["label_name"],
            pressing_text=data["pressing_text"],
            barcode=data["barcode"],
            runout_side_a=data["runout_side_a"],
            runout_side_b=data["runout_side_b"],
            image_url=data["image_url"],
        )
        self.db.add(release)
        self.db.flush()

        for artist_data in data["artists"]:
            artist_mapping = None
            ext_artist_id = artist_data.get("discogs_artist_id")
            if ext_artist_id:
                artist_mapping = self.db.scalar(
                    select(ExternalMapping).where(
                        ExternalMapping.provider == "discogs",
                        ExternalMapping.entity_type == "artist",
                        ExternalMapping.external_id == ext_artist_id,
                    )
                )

            artist = self.db.get(Artist, artist_mapping.entity_id) if artist_mapping else None
            if artist is None:
                artist = Artist(name=artist_data["name"])
                self.db.add(artist)
                self.db.flush()
                if ext_artist_id:
                    self.db.add(
                        ExternalMapping(
                            provider="discogs",
                            entity_type="artist",
                            entity_id=artist.id,
                            external_id=ext_artist_id,
                        )
                    )

            self.db.add(
                ReleaseArtist(
                    release_id=release.id,
                    artist_id=artist.id,
                    role="primary",
                )
            )

        self.db.add(
            ExternalMapping(
                provider="discogs",
                entity_type="release",
                entity_id=release.id,
                external_id=str(discogs_release_id),
            )
        )
        self.db.flush()
        return release, True, raw
