from dataclasses import dataclass
from typing import Any

CONDITION_SCORE = {"M":100,"NM":96,"NM-":92,"VG+":86,"VG":72,"G+":58,"G":45,"F":25,"P":10}

@dataclass
class ScoreInput:
    asking_price: float
    estimated_low: float | None = None
    estimated_high: float | None = None
    owned: bool = False
    on_wantlist: bool = False
    collector_match: int = 50
    media_condition: str | None = None
    pressing_match: int = 50
    listing_confidence: int = 70

def calculate_spinninglicorice_score(data: ScoreInput) -> dict[str, Any]:
    if data.estimated_low and data.estimated_high:
        midpoint = (data.estimated_low + data.estimated_high) / 2
        ratio = data.asking_price / midpoint if midpoint else 1
        if ratio <= 0.55: price_score = 100
        elif ratio <= 0.75: price_score = 90
        elif ratio <= 0.95: price_score = 75
        elif ratio <= 1.10: price_score = 58
        elif ratio <= 1.30: price_score = 40
        else: price_score = 20
    else:
        price_score = 55

    gap_score = 20 if data.owned else (100 if data.on_wantlist else 72)
    condition_score = CONDITION_SCORE.get((data.media_condition or "").upper(), 65)

    score = round(
        data.collector_match * 0.25 +
        price_score * 0.25 +
        gap_score * 0.20 +
        data.pressing_match * 0.10 +
        condition_score * 0.10 +
        data.listing_confidence * 0.10
    )
    score = max(0, min(100, score))

    if score >= 90: label = "GREAT BUY"
    elif score >= 80: label = "GOOD BUY"
    elif score >= 65: label = "FAIR"
    elif score >= 50: label = "WATCH"
    else: label = "SKIP"

    return {
        "score": score,
        "deal_label": label,
        "breakdown": {
            "collector_match": round(data.collector_match),
            "price": round(price_score),
            "collection_gap": round(gap_score),
            "pressing": round(data.pressing_match),
            "condition": round(condition_score),
            "listing_confidence": round(data.listing_confidence),
        },
    }
