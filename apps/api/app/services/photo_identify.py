"""Identify a record from a photo of its cover or center label, using Claude's
vision capability, then search Discogs for matches.

This is deliberately positioned as a *secondary* option to barcode scanning,
not a replacement — image identification of album art is inherently less
reliable than reading a printed barcode (lighting, angle, and reissues that
share cover art all trip it up). The UI should present it that way, and this
module reflects that: it always returns the AI's raw guess alongside the
Discogs candidates, so a wrong guess is visible rather than silently trusted.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.services.ai.client import AIClient
from app.services.collection_edit import search_discogs

_SYSTEM = """You are looking at a single photo of a vinyl record — either its \
cover art or its printed center label. Identify the artist and the album or \
release title if you can tell from what's visible.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{"artist": string or null, "title": string or null, "confidence": "high" | "medium" | "low", "notes": string}

Rules:
- If you cannot make out enough to identify it, set "artist" and "title" to null and explain briefly in "notes".
- "confidence" should reflect how sure you are, not how clearly you can see the image.
- Do not guess a specific pressing, year, or catalog number from a cover alone — that's beyond what a cover photo can tell you.
- Keep "notes" to one short sentence."""

_USER_TEXT = "Identify this vinyl record from the photo. Respond with only the JSON object described in the system prompt."


def identify_and_search(
    db: Session,
    user_id: uuid.UUID,
    image_bytes: bytes,
    media_type: str,
    *,
    limit: int = 10,
) -> dict:
    """Returns {"identified": {...AI guess...}, "results": [...Discogs candidates...]}.

    Raises RuntimeError if AI isn't configured, or if identification produced
    nothing usable to search with. A downstream RuntimeError from Discogs
    (e.g. "connect your account first") propagates as-is.
    """
    ai = AIClient()
    if not ai.is_enabled:
        raise RuntimeError("Photo identification isn't available on this server yet.")

    guess = ai.identify_image(_SYSTEM, _USER_TEXT, image_bytes, media_type)
    if not guess:
        raise RuntimeError("Couldn't reach the identification service. Try again, or use the barcode instead.")

    artist = (guess.get("artist") or "").strip()
    title = (guess.get("title") or "").strip()
    confidence = guess.get("confidence") or "low"
    notes = guess.get("notes") or ""

    identified = {"artist": artist or None, "title": title or None, "confidence": confidence, "notes": notes}

    if not artist and not title:
        # Nothing to search with — return the (empty) guess so the UI can
        # show *why* rather than a generic error.
        return {"identified": identified, "results": []}

    query = " ".join(part for part in (artist, title) if part)
    results = search_discogs(db, user_id, query, limit=limit)
    return {"identified": identified, "results": results}
