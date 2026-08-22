"""Central affiliate / referral link builder.

One place that turns a destination into an outbound partner link, carrying your
tracking tag when configured. Every function degrades to a plain, working link
when the matching ID/provider isn't set — so nothing breaks before you're
approved, and links start earning the moment you fill in the env var.

Covered partners:
  * Tickets      - SeatGeek / StubHub / Vivid Seats / Ticketmaster
  * Rental cars  - Expedia / Rentalcars.com / Discover Cars
  * Rideshare    - a referral URL you paste (Uber/Lyft)
  * Hotels/flights - see trip_planner.py (Expedia), kept there for trip context.

All links are for the user's benefit and are marked rel="sponsored nofollow"
in the UI. No prices are set or money handled here — these are outbound links.
"""
from __future__ import annotations

from urllib.parse import quote_plus, urlencode

from app.core.config import settings


def _append(url: str, params: dict) -> str:
    if not params:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urlencode(params)}"


# ---- Tickets ---------------------------------------------------------------

def ticket_link(event_name: str, city: str | None, fallback_url: str | None) -> dict:
    """Build a ticket link for an event.

    Returns {"url", "provider", "affiliate": bool}. If no affiliate provider is
    configured we return the event's own ticket URL (or a SeatGeek search) with
    affiliate=False.
    """
    provider = settings.ticket_affiliate_provider.lower().strip()
    aff = settings.ticket_affiliate_id.strip()
    q = " ".join([p for p in [event_name, city] if p])

    if provider and aff:
        if provider == "seatgeek":
            url = _append(
                f"https://seatgeek.com/search?q={quote_plus(q)}",
                {"aid": aff},
            )
        elif provider == "stubhub":
            url = _append(
                f"https://www.stubhub.com/find/s/?q={quote_plus(q)}",
                {"gcid": aff},
            )
        elif provider == "vividseats":
            url = _append(
                f"https://www.vividseats.com/search?searchTerm={quote_plus(q)}",
                {"wsUser": aff},
            )
        elif provider == "ticketmaster":
            url = _append(
                f"https://www.ticketmaster.com/search?q={quote_plus(q)}",
                {"camefrom": aff},
            )
        else:
            url = None
        if url:
            return {"url": url, "provider": provider, "affiliate": True}

    # Fallback: the event's own link, else a plain SeatGeek search.
    url = fallback_url or f"https://seatgeek.com/search?q={quote_plus(q)}"
    return {"url": url, "provider": provider or "tickets", "affiliate": False}


# ---- Rental cars -----------------------------------------------------------

def car_rental_link(city: str, pickup_date: str | None, dropoff_date: str | None) -> dict:
    provider = settings.car_affiliate_provider.lower().strip()
    aff = settings.car_affiliate_id.strip()

    if provider == "rentalcars" and aff:
        url = _append(
            f"https://www.rentalcars.com/SearchResults.do?location={quote_plus(city)}",
            {"affiliateCode": aff},
        )
        return {"url": url, "provider": "rentalcars", "affiliate": True}
    if provider == "discovercars" and aff:
        url = _append(
            f"https://www.discovercars.com/search?location={quote_plus(city)}",
            {"a_aid": aff},
        )
        return {"url": url, "provider": "discovercars", "affiliate": True}

    # Default: Expedia cars (reuses the Expedia affiliate tag if present).
    base = f"https://www.expedia.com/Car-Search?locn={quote_plus(city)}"
    if pickup_date:
        base += f"&date1={pickup_date}"
    if dropoff_date:
        base += f"&date2={dropoff_date}"
    exp = settings.expedia_affiliate_id.strip()
    if exp:
        return {"url": _append(base, {"affcid": exp}), "provider": "expedia", "affiliate": True}
    return {"url": base, "provider": "expedia", "affiliate": False}


# ---- Rideshare -------------------------------------------------------------

def rideshare_link() -> dict | None:
    """A rideshare referral link, if you've set one. Returns None when unset
    (nothing to show)."""
    url = settings.rideshare_referral_url.strip()
    if not url:
        return None
    provider = settings.rideshare_provider.lower().strip() or "rideshare"
    return {"url": url, "provider": provider, "affiliate": True}
