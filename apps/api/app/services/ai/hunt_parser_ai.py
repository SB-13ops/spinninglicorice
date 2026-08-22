"""Natural-language hunt-query parsing, powered by Claude with a regex fallback.

`parse_hunt_query_smart` tries Claude (fast model, structured JSON) first and
falls back to the existing regex parser (`parse_hunt_query`) whenever the AI is
disabled, errors, or returns something malformed. The output shape is identical
either way, so callers don't care which path produced it.
"""
from __future__ import annotations

from typing import Any

from app.services.ai.client import get_ai
from app.services.hunt_parser import parse_hunt_query

_SYSTEM = """You extract structured search criteria from a vinyl-record collector's \
natural-language "hunt" request. Return ONLY a JSON object, no prose, with exactly these keys:

- "artists": array of artist name strings (empty if none named)
- "max_price": number or null (a price ceiling, in the query's currency)
- "minimum_condition": one of "NM","VG+","VG","G+","G","F","P" or null (media grade)
- "ownership": "not_owned" if they want records they don't already own, else "any"
- "wantlist_only": true if they restrict to their wantlist, else false
- "year_start": integer year or null
- "year_end": integer year or null
- "early_pressing_preferred": true if they want first/original/early pressings, else false

Infer only what is clearly stated or strongly implied. Do not invent artists or years."""

_ALLOWED_CONDITIONS = {"NM", "VG+", "VG", "G+", "G", "F", "P"}


def parse_hunt_query_smart(query: str) -> dict[str, Any]:
    ai = get_ai()
    if ai.is_enabled:
        parsed = ai.complete_json(_SYSTEM, query.strip(), max_tokens=400)
        normalized = _validate(parsed, query)
        if normalized is not None:
            return normalized
    # Fallback: deterministic regex parser.
    return parse_hunt_query(query)


def _validate(parsed: dict | None, query: str) -> dict[str, Any] | None:
    """Coerce the model output into the exact criteria shape, or None if unusable."""
    if not isinstance(parsed, dict):
        return None
    try:
        artists = parsed.get("artists") or []
        if not isinstance(artists, list):
            return None
        artists = [str(a).strip() for a in artists if str(a).strip()]

        max_price = parsed.get("max_price")
        max_price = float(max_price) if isinstance(max_price, (int, float)) else None

        cond = parsed.get("minimum_condition")
        cond = cond if cond in _ALLOWED_CONDITIONS else None

        ownership = "not_owned" if parsed.get("ownership") == "not_owned" else "any"
        wantlist_only = bool(parsed.get("wantlist_only"))
        early = bool(parsed.get("early_pressing_preferred"))

        ys = parsed.get("year_start")
        ye = parsed.get("year_end")
        ys = int(ys) if isinstance(ys, (int, float)) else None
        ye = int(ye) if isinstance(ye, (int, float)) else None

        return {
            "artists": artists,
            "max_price": max_price,
            "minimum_condition": cond,
            "ownership": ownership,
            "wantlist_only": wantlist_only,
            "year_start": ys,
            "year_end": ye,
            "early_pressing_preferred": early,
            "raw_query": query.strip(),
        }
    except (TypeError, ValueError):
        return None
