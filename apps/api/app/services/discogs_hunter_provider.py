from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    CollectionItem,
    ExternalAccount,
    Release,
    User,
    WantlistItem,
)
from app.services.discogs_client import DiscogsClient, client_for_account
from app.services.discogs_sync import DiscogsSyncService


@dataclass
class DiscogsOpportunity:
    discogs_release_id: str
    spinninglicorice_release_id: UUID
    title: str
    artist: str
    year: int | None
    country: str | None
    image_url: str | None
    current_lowest_price: float | None
    num_for_sale: int
    estimated_low: float | None
    estimated_high: float | None
    media_condition_basis: str | None
    owned: bool
    on_wantlist: bool
    marketplace_url: str


class DiscogsHunterProvider:
    """Real Discogs marketplace-value provider.

    V1 uses Discogs database search + release marketplace summary data and
    pricing suggestions. It does not scrape individual seller listings.
    """

    def __init__(self, db: Session, *, user: User):
        self.db = db
        self.user = user
        self.account = db.scalar(
            select(ExternalAccount).where(
                ExternalAccount.user_id == user.id,
                ExternalAccount.provider == "discogs",
            )
        )
        if not self.account:
            raise RuntimeError("Discogs is not connected.")

        self.client = client_for_account(self.account)
        self.sync_service = DiscogsSyncService(db, self.client)

    def search(self, criteria: dict[str, Any], *, limit: int = 12) -> list[DiscogsOpportunity]:
        artist = (criteria.get("artists") or [None])[0]
        year = criteria.get("year_start")
        if criteria.get("year_end") != year:
            year = None

        query = criteria.get("raw_query") or None
        payload = self.client.database_search(
            query=None if artist else query,
            artist=artist,
            year=year,
            country=None,
            per_page=min(max(limit * 2, 10), 50),
            page=1,
        )

        results = []
        for row in payload.get("results", []):
            discogs_id = row.get("id")
            if discogs_id is None:
                continue

            try:
                release, _created, release_payload = (
                    self.sync_service._get_or_import_release_with_payload(discogs_id)
                )
                self.db.flush()

                # Reuse the payload from the import when we just fetched it. On a
                # DB cache-hit (payload is None) fall back to client.release(),
                # which is itself response-cached, so it's cheap.
                if release_payload is None:
                    release_payload = self.client.release(discogs_id)
                suggestions = self.client.price_suggestions(discogs_id)

                lowest_price = _money_value(release_payload.get("lowest_price"))
                num_for_sale = int(release_payload.get("num_for_sale") or 0)

                condition = criteria.get("minimum_condition") or "Very Good Plus (VG+)"
                estimated_low, estimated_high, basis = _estimate_range(suggestions, condition)

                max_price = criteria.get("max_price")
                if max_price is not None and lowest_price is not None and lowest_price > float(max_price):
                    continue

                owned = self.db.scalar(
                    select(CollectionItem.id).where(
                        CollectionItem.user_id == self.user.id,
                        CollectionItem.release_id == release.id,
                    ).limit(1)
                ) is not None

                on_wantlist = self.db.scalar(
                    select(WantlistItem.id).where(
                        WantlistItem.user_id == self.user.id,
                        WantlistItem.release_id == release.id,
                    ).limit(1)
                ) is not None

                if criteria.get("ownership") == "not_owned" and owned:
                    continue
                if criteria.get("wantlist_only") and not on_wantlist:
                    continue

                artists = release_payload.get("artists") or []
                artist_name = ", ".join(
                    a.get("name") for a in artists if a.get("name")
                ) or (artist or "Unknown Artist")

                results.append(
                    DiscogsOpportunity(
                        discogs_release_id=str(discogs_id),
                        spinninglicorice_release_id=release.id,
                        title=release.title,
                        artist=artist_name,
                        year=release.release_year,
                        country=release.country,
                        image_url=release.image_url,
                        current_lowest_price=lowest_price,
                        num_for_sale=num_for_sale,
                        estimated_low=estimated_low,
                        estimated_high=estimated_high,
                        media_condition_basis=basis,
                        owned=owned,
                        on_wantlist=on_wantlist,
                        marketplace_url=f"https://www.discogs.com/sell/release/{discogs_id}",
                    )
                )
            except Exception:
                # One malformed/unavailable release should not kill the whole
                # Hunt, but log it (with the id) so systemic failures — expired
                # token, rate-limit, Discogs outage — are visible in the logs
                # rather than looking identical to "no results".
                import logging

                logging.getLogger("spinninglicorice.hunter").warning(
                    "Skipping Discogs release %s during hunt", discogs_id, exc_info=True
                )
                continue

            if len(results) >= limit:
                break

        self.db.commit()
        return results


def _money_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _estimate_range(
    suggestions: dict[str, Any],
    preferred_condition: str,
) -> tuple[float | None, float | None, str | None]:
    if not suggestions:
        return None, None, None

    aliases = [
        preferred_condition,
        "Very Good Plus (VG+)",
        "Near Mint (NM or M-)",
        "Very Good (VG)",
    ]
    chosen_value = None
    chosen_label = None

    for label in aliases:
        if label in suggestions:
            chosen_value = _money_value(suggestions[label])
            chosen_label = label
            if chosen_value is not None:
                break

    values = [
        _money_value(v)
        for v in suggestions.values()
    ]
    values = [v for v in values if v is not None and v > 0]

    if chosen_value is not None:
        return round(chosen_value * 0.85, 2), round(chosen_value * 1.15, 2), chosen_label

    if values:
        values.sort()
        low = values[max(0, int(len(values) * 0.25) - 1)]
        high = values[min(len(values) - 1, int(len(values) * 0.75))]
        return round(low, 2), round(high, 2), "Discogs condition suggestions"

    return None, None, None
