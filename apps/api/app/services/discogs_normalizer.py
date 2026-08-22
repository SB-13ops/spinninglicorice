from __future__ import annotations

from typing import Any


def normalize_release_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a Discogs release response into Burnt Jacket catalog fields."""
    artists = [
        {
            "name": artist.get("name"),
            "discogs_artist_id": str(artist.get("id")) if artist.get("id") is not None else None,
        }
        for artist in payload.get("artists", [])
        if artist.get("name")
    ]

    labels = payload.get("labels") or []
    first_label = labels[0] if labels else {}

    images = payload.get("images") or []
    primary = next((img for img in images if img.get("type") == "primary"), None)
    image_url = (primary or (images[0] if images else {})).get("uri")

    formats = payload.get("formats") or []
    pressing_parts: list[str] = []
    for fmt in formats:
        if fmt.get("name"):
            pressing_parts.append(fmt["name"])
        pressing_parts.extend(fmt.get("descriptions") or [])

    return {
        "title": payload.get("title") or "Unknown Release",
        "release_year": payload.get("year") or None,
        "country": payload.get("country"),
        "catalog_number": first_label.get("catno"),
        "label_name": first_label.get("name"),
        "pressing_text": " · ".join(dict.fromkeys(pressing_parts)) or None,
        "barcode": _first_identifier(payload, "Barcode"),
        "runout_side_a": _runout(payload, "A"),
        "runout_side_b": _runout(payload, "B"),
        "image_url": image_url,
        "artists": artists,
        "genres": payload.get("genres") or [],
        "styles": payload.get("styles") or [],
        "discogs_release_id": str(payload.get("id")),
    }


def _first_identifier(payload: dict[str, Any], identifier_type: str) -> str | None:
    for identifier in payload.get("identifiers") or []:
        if identifier.get("type") == identifier_type:
            return identifier.get("value")
    return None


def _runout(payload: dict[str, Any], side: str) -> str | None:
    for identifier in payload.get("identifiers") or []:
        if identifier.get("type") != "Matrix / Runout":
            continue
        description = (identifier.get("description") or "").upper()
        if f"SIDE {side}" in description or description == side:
            return identifier.get("value")
    return None
