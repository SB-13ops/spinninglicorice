from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class ScoutScoreInput:
    artist_match: int
    related_artist_match: int = 50
    genre_match: int = 50
    distance_score: int = 70
    event_confidence: int = 90

def calculate_scout_score(data: ScoutScoreInput) -> dict[str, Any]:
    score = round(
        data.artist_match * 0.40
        + data.related_artist_match * 0.20
        + data.genre_match * 0.15
        + data.distance_score * 0.15
        + data.event_confidence * 0.10
    )
    score = max(0, min(100, score))
    if score >= 92:
        label = "DON'T MISS"
    elif score >= 84:
        label = "STRONG MATCH"
    elif score >= 72:
        label = "GOOD MATCH"
    elif score >= 60:
        label = "WORTH A LOOK"
    else:
        label = "DISCOVERY"

    return {
        "score": score,
        "label": label,
        "breakdown": {
            "artist_match": data.artist_match,
            "related_artist_match": data.related_artist_match,
            "genre_match": data.genre_match,
            "distance": data.distance_score,
            "event_confidence": data.event_confidence,
        },
    }
