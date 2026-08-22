from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import CollectorAffinity, Event, ScoutRecommendation, User, UserPreference
from app.services.scout_score import ScoutScoreInput, calculate_scout_score
from app.services.ticketmaster_client import TicketmasterClient


def _norm(s: str | None) -> str:
    return " ".join((s or "").lower().replace("&", "and").split())


class ScoutService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def build_recommendations(self, *, limit: int = 20) -> list[dict[str, Any]]:
        prefs = self.db.get(UserPreference, self.user.id)
        postal_code = None
        radius = 25
        if prefs:
            radius = prefs.radius_miles or 25
            # V1 accepts ZIP/postal code in location_text if present.
            if prefs.location_text and any(c.isdigit() for c in prefs.location_text):
                postal_code = prefs.location_text.strip()

        affinities = self.db.execute(
            select(CollectorAffinity)
            .where(
                CollectorAffinity.user_id == self.user.id,
                CollectorAffinity.affinity_type == "artist",
            )
            .order_by(CollectorAffinity.score.desc())
            .limit(12)
        ).scalars().all()

        top_artists = [a.affinity_key for a in affinities]
        if not top_artists:
            return []

        client = TicketmasterClient()
        seen_events: set[str] = set()
        built: list[dict[str, Any]] = []

        # Query strongest artists independently. This improves precision and gives
        # us a clear explanation for why the event is recommended.
        for rank, artist_name in enumerate(top_artists[:8]):
            try:
                payload = client.search_events(
                    keyword=artist_name,
                    postal_code=postal_code,
                    radius=radius,
                    size=15,
                )
            except Exception:
                continue

            events = (payload.get("_embedded") or {}).get("events") or []
            for raw in events:
                external_id = raw.get("id")
                if not external_id or external_id in seen_events:
                    continue
                seen_events.add(external_id)

                attractions = (raw.get("_embedded") or {}).get("attractions") or []
                attraction_names = [a.get("name") for a in attractions if a.get("name")]
                exact = any(_norm(artist_name) == _norm(n) for n in attraction_names)

                classifications = raw.get("classifications") or []
                genre_name = None
                if classifications:
                    genre_name = ((classifications[0].get("genre") or {}).get("name"))

                venue = (((raw.get("_embedded") or {}).get("venues") or [{}])[0])
                city = (venue.get("city") or {}).get("name")
                region = (venue.get("state") or {}).get("stateCode") or (venue.get("state") or {}).get("name")
                venue_name = venue.get("name")

                start = raw.get("dates", {}).get("start", {})
                starts_at = start.get("dateTime") or start.get("localDate")
                if not starts_at:
                    continue

                # Rank-based affinity gives strong known-artist recommendations.
                artist_match = 98 if exact else max(72, 92 - rank * 3)
                genre_match = 82 if genre_name and genre_name.lower() in {"rock", "alternative", "country", "folk"} else 70
                distance_score = 80 if postal_code else 68

                score_data = calculate_scout_score(
                    ScoutScoreInput(
                        artist_match=artist_match,
                        related_artist_match=78,
                        genre_match=genre_match,
                        distance_score=distance_score,
                        event_confidence=92,
                    )
                )

                event = self.db.scalar(
                    select(Event).where(
                        Event.provider == "ticketmaster",
                        Event.external_event_id == external_id,
                    )
                )
                if event is None:
                    event = Event(
                        provider="ticketmaster",
                        external_event_id=external_id,
                        name=raw.get("name") or artist_name,
                        venue_name=venue_name,
                        city=city,
                        region=region,
                        starts_at=starts_at,
                        ticket_url=raw.get("url"),
                    )
                    self.db.add(event)
                    self.db.flush()

                existing = self.db.scalar(
                    select(ScoutRecommendation).where(
                        ScoutRecommendation.user_id == self.user.id,
                        ScoutRecommendation.event_id == event.id,
                    )
                )
                reason = (
                    f"Your collection strongly signals {artist_name}. "
                    f"{'Exact artist match.' if exact else 'Strong related-event match.'}"
                )
                evidence = {
                    "matched_artist": artist_name,
                    "attractions": attraction_names,
                    "genre": genre_name,
                    "source": "ticketmaster",
                    "score_breakdown": score_data["breakdown"],
                }

                if existing is None:
                    existing = ScoutRecommendation(
                        user_id=self.user.id,
                        event_id=event.id,
                        match_score=score_data["score"],
                        reason=reason,
                        evidence=evidence,
                    )
                    self.db.add(existing)
                else:
                    existing.match_score = score_data["score"]
                    existing.reason = reason
                    existing.evidence = evidence

                built.append({
                    "event_id": str(event.id),
                    "name": event.name,
                    "venue": event.venue_name,
                    "city": event.city,
                    "region": event.region,
                    "starts_at": str(event.starts_at),
                    "ticket_url": event.ticket_url,
                    "match_score": score_data["score"],
                    "match_label": score_data["label"],
                    "reason": reason,
                    "matched_artist": artist_name,
                    "genre": genre_name,
                })

        self.db.commit()
        built.sort(key=lambda x: x["match_score"], reverse=True)
        return built[:limit]
