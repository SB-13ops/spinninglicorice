from __future__ import annotations
from typing import Any
import httpx
from app.core.config import settings

BASE_URL = "https://app.ticketmaster.com/discovery/v2"

class TicketmasterClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.ticketmaster_api_key or settings.concert_provider_api_key

    def search_events(
        self,
        *,
        keyword: str | None = None,
        postal_code: str | None = None,
        radius: int = 25,
        unit: str = "miles",
        size: int = 50,
        page: int = 0,
        classification_name: str = "music",
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Ticketmaster API key is not configured.")
        params: dict[str, Any] = {
            "apikey": self.api_key,
            "radius": radius,
            "unit": unit,
            "size": size,
            "page": page,
            "classificationName": classification_name,
            "sort": "date,asc",
        }
        if keyword:
            params["keyword"] = keyword
        if postal_code:
            params["postalCode"] = postal_code

        with httpx.Client(timeout=30) as client:
            r = client.get(f"{BASE_URL}/events.json", params=params)
            r.raise_for_status()
            return r.json()
