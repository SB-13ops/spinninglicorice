"""Concert road-trip planner.

Builds a trip plan and cost estimate from an origin to a concert:

  * Gas cost is computed deterministically (distance x price / MPG).
  * Driving distance/time and *estimated* hotel & flight price ranges come from
    an AI web search (clearly labeled estimates, with citations) when AI is
    enabled; otherwise those fields are left null and only the gas + plan show.
  * Booking deep-links point at Expedia, carrying the configured affiliate tag
    when present (plain search links otherwise).

Nothing here books or charges anything — it's planning + estimates + outbound
links. All monetary figures are estimates; the site-wide AI disclosure applies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from app.core.config import settings
from app.services.ai.client import get_ai


@dataclass
class CostLine:
    label: str
    amount: float | None            # None = couldn't estimate
    detail: str | None = None
    estimated: bool = True          # False for the deterministic gas figure


@dataclass
class TripPlan:
    destination: str
    origin: str
    mode: str                       # "drive" | "fly" | "compare"
    nights: int
    itinerary: list[str] = field(default_factory=list)
    costs: list[CostLine] = field(default_factory=list)
    total_low: float | None = None
    total_high: float | None = None
    booking_links: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)


# ---- Expedia deep links -----------------------------------------------------

def _tag(url: str) -> str:
    aff = settings.expedia_affiliate_id
    if not aff:
        return url
    sep = "&" if "?" in url else "?"
    # Expedia affiliate deep-links carry a tracking ID; the exact param name
    # depends on your program (CJ vs Partnerize vs Creator). We use a generic
    # `siteid`/`clickref`-style tag param that you can adjust to your program.
    return f"{url}{sep}affcid={quote_plus(aff)}"


def expedia_hotel_link(city: str, checkin: str | None, checkout: str | None) -> str:
    base = f"https://www.expedia.com/Hotel-Search?destination={quote_plus(city)}"
    if checkin:
        base += f"&startDate={checkin}"
    if checkout:
        base += f"&endDate={checkout}"
    return _tag(base)


def expedia_flight_link(origin: str, dest_city: str, depart: str | None, ret: str | None) -> str:
    base = (
        "https://www.expedia.com/Flights-Search?trip=roundtrip"
        f"&leg1=from:{quote_plus(origin)},to:{quote_plus(dest_city)}"
    )
    if depart:
        base += f",departure:{depart}"
    if ret:
        base += f"&leg2=from:{quote_plus(dest_city)},to:{quote_plus(origin)},departure:{ret}"
    return _tag(base)


# ---- Gas math (deterministic) ----------------------------------------------

def gas_cost(distance_miles: float, mpg: float, gas_price: float, round_trip: bool = True) -> float:
    miles = distance_miles * (2 if round_trip else 1)
    return round((miles / max(mpg, 1)) * gas_price, 2)


# ---- AI trip research -------------------------------------------------------

_TRIP_SYSTEM = """You are a travel-logistics estimator. Given an origin, a destination \
city, and dates, use web search to return ROUGH current estimates. Reply as compact JSON \
ONLY, no prose, with these keys:
- "drive_distance_miles": number or null (one-way driving distance)
- "drive_time_hours": number or null (one-way)
- "hotel_per_night_low": number or null (USD, typical mid-range)
- "hotel_per_night_high": number or null (USD)
- "flight_roundtrip_low": number or null (USD per person)
- "flight_roundtrip_high": number or null (USD per person)
All figures are rough estimates for planning only. Use null when you can't find a basis."""


def _ai_trip_estimates(origin: str, dest_city: str, depart: str, ret: str):
    ai = get_ai()
    if not ai.is_enabled:
        return None, []
    user = (
        f"Origin: {origin}. Destination city: {dest_city}. "
        f"Depart {depart}, return {ret}. Estimate driving distance/time, "
        f"mid-range hotel per-night range, and round-trip flight range."
    )
    result = ai.research(_TRIP_SYSTEM, user, max_tokens=700)
    if result is None:
        return None, []
    from app.services.ai.client import _extract_json  # reuse tolerant parser

    data = _extract_json(result.text)
    return data, result.citations


# ---- Plan builder -----------------------------------------------------------

def build_trip_plan(
    *,
    origin: str,
    dest_city: str,
    event_name: str,
    venue: str | None,
    starts_at: datetime,
    mode: str = "compare",
    nights: int = 1,
    mpg: float = 28.0,
    gas_price: float | None = None,
    travelers: int = 1,
) -> TripPlan:
    gas_price = gas_price if gas_price is not None else settings.default_gas_price_usd
    depart_date = (starts_at - timedelta(days=1)).date().isoformat()
    return_date = (starts_at + timedelta(days=max(nights - 1, 0))).date().isoformat()
    checkin = depart_date
    checkout = (starts_at + timedelta(days=max(nights - 1, 0))).date().isoformat()

    plan = TripPlan(destination=dest_city, origin=origin, mode=mode, nights=nights)

    # AI estimates (distance, hotel, flight). Deterministic gas is layered on top.
    est, citations = _ai_trip_estimates(origin, dest_city, depart_date, return_date)
    plan.citations = citations or []

    distance = _num(est, "drive_distance_miles") if est else None
    drive_hours = _num(est, "drive_time_hours") if est else None
    hotel_low = _num(est, "hotel_per_night_low") if est else None
    hotel_high = _num(est, "hotel_per_night_high") if est else None
    flight_low = _num(est, "flight_roundtrip_low") if est else None
    flight_high = _num(est, "flight_roundtrip_high") if est else None

    total_low = 0.0
    total_high = 0.0

    # Driving costs
    if mode in ("drive", "compare"):
        if distance is not None:
            g = gas_cost(distance, mpg, gas_price, round_trip=True)
            plan.costs.append(
                CostLine("Gas (round trip)", g, f"{distance:.0f} mi each way @ {mpg:.0f} MPG, ${gas_price:.2f}/gal", estimated=False)
            )
            total_low += g
            total_high += g
        else:
            plan.costs.append(CostLine("Gas (round trip)", None, "Couldn't estimate distance", estimated=False))

    # Flight costs
    if mode in ("fly", "compare"):
        if flight_low is not None:
            fl = flight_low * travelers
            fh = (flight_high or flight_low) * travelers
            plan.costs.append(
                CostLine("Flights (round trip)", None,
                         f"~${flight_low:.0f}–${(flight_high or flight_low):.0f} pp × {travelers}", estimated=True)
            )
            plan.costs[-1].amount = round((fl + fh) / 2, 2)
            if mode == "fly":
                total_low += fl
                total_high += fh

    # Hotel costs
    if hotel_low is not None and nights > 0:
        hl = hotel_low * nights
        hh = (hotel_high or hotel_low) * nights
        plan.costs.append(
            CostLine("Hotel", round((hl + hh) / 2, 2),
                     f"{nights} night(s) @ ~${hotel_low:.0f}–${(hotel_high or hotel_low):.0f}/night", estimated=True)
        )
        total_low += hl
        total_high += hh

    plan.total_low = round(total_low, 2) if total_low else None
    plan.total_high = round(total_high, 2) if total_high else None

    # Itinerary
    show_day = starts_at.strftime("%a %b %d")
    if mode in ("drive", "compare") and drive_hours:
        plan.itinerary.append(f"Depart {origin} ~{drive_hours:.0f} h drive to {dest_city}")
    else:
        plan.itinerary.append(f"Travel from {origin} to {dest_city}")
    if nights > 0:
        plan.itinerary.append(f"Check in near {venue or dest_city} ({nights} night(s))")
    plan.itinerary.append(f"{event_name} — {show_day}")
    plan.itinerary.append(f"Return to {origin}")

    # Booking links (always present; carry affiliate tag when configured)
    from app.services.affiliate_links import car_rental_link, rideshare_link

    plan.booking_links = {
        "hotel": expedia_hotel_link(dest_city, checkin, checkout),
        "flight": expedia_flight_link(origin, dest_city, depart_date, return_date),
        "car": car_rental_link(dest_city, depart_date, return_date)["url"],
        "affiliate_active": bool(settings.expedia_affiliate_id),
    }
    ride = rideshare_link()
    if ride:
        plan.booking_links["rideshare"] = ride["url"]

    plan.notes.append("All prices are rough estimates for planning only — verify before booking.")
    if not get_ai().is_enabled:
        plan.notes.append("AI estimates are off (no API key); showing gas + plan only.")

    return plan


def _num(d: dict | None, key: str) -> float | None:
    if not d:
        return None
    v = d.get(key)
    return float(v) if isinstance(v, (int, float)) else None
