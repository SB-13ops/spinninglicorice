from __future__ import annotations
import re
from typing import Any

CONDITION_PATTERN = re.compile(r"\b(NM-?|VG\+|VG|G\+|G|F|P)\b", re.IGNORECASE)
PRICE_PATTERN = re.compile(r"(?:under|below|max(?:imum)?|<=?)\s*\$?\s*(\d+(?:\.\d{1,2})?)", re.IGNORECASE)
YEAR_RANGE_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\s*[-–]\s*(19\d{2}|20\d{2})\b")
YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")

def parse_hunt_query(query: str) -> dict[str, Any]:
    q = query.strip()
    q_lower = q.lower()
    price_match = PRICE_PATTERN.search(q)
    max_price = float(price_match.group(1)) if price_match else None
    condition_match = CONDITION_PATTERN.search(q)
    minimum_condition = condition_match.group(1).upper() if condition_match else None

    year_start = year_end = None
    yrange = YEAR_RANGE_PATTERN.search(q)
    if yrange:
        year_start, year_end = int(yrange.group(1)), int(yrange.group(2))
    else:
        years = [int(y) for y in YEAR_PATTERN.findall(q)]
        if years:
            year_start = year_end = years[0]

    ownership = "not_owned" if any(
        x in q_lower for x in ["don't own", "do not own", "missing", "not owned", "i'm missing"]
    ) else "any"

    wantlist_only = "wantlist" in q_lower
    early_pressing = any(
        x in q_lower for x in ["first pressing", "first press", "early pressing", "original pressing"]
    )

    criteria_markers = [
        " under ", " below ", " for under ", " i don't own", " i do not own",
        " i'm missing", " missing ", " first pressing", " early pressing",
        " original pressing", " vg", " nm", " from "
    ]
    cut_positions = [q_lower.find(m) for m in criteria_markers if q_lower.find(m) > 0]
    artist_guess = q[:min(cut_positions)].strip(" ,.-") if cut_positions else q

    generic_starts = (
        "find interesting", "find records", "records", "albums",
        "psychedelic rock", "rare records", "first pressings"
    )
    artists = []
    if artist_guess and not artist_guess.lower().startswith(generic_starts):
        artist_guess = re.sub(r"^(find|show me|hunt|search for)\s+", "", artist_guess, flags=re.I).strip()
        if artist_guess:
            artists = [artist_guess]

    return {
        "artists": artists,
        "max_price": max_price,
        "minimum_condition": minimum_condition,
        "ownership": ownership,
        "wantlist_only": wantlist_only,
        "year_start": year_start,
        "year_end": year_end,
        "early_pressing_preferred": early_pressing,
        "raw_query": q,
    }
