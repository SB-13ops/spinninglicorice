from dataclasses import dataclass
from typing import Any

@dataclass
class DemoListing:
    external_listing_id: str
    title_raw: str
    price: float
    shipping: float
    media_condition: str
    sleeve_condition: str
    seller_name: str
    listing_url: str
    estimated_low: float
    estimated_high: float
    artist: str
    year: int | None = None
    country: str | None = "US"

DEMO_LISTINGS = [
    DemoListing("demo-001","Grateful Dead - Blues For Allah 1975 US LP",18,5,"VG+","VG+","Demo Records","https://example.invalid/demo-001",35,55,"Grateful Dead",1975),
    DemoListing("demo-002","Grateful Dead - Aoxomoxoa US pressing",32,6,"VG+","VG","Demo Vinyl","https://example.invalid/demo-002",38,60,"Grateful Dead",1969),
    DemoListing("demo-003","Jerry Garcia - Garcia 1972 LP",24,5,"VG+","VG+","Demo Wax","https://example.invalid/demo-003",35,50,"Jerry Garcia",1972),
    DemoListing("demo-004","Old & In The Way - Old & In The Way",27,5,"VG+","VG+","Demo Crates","https://example.invalid/demo-004",40,62,"Old & In the Way",1975),
]

def search_demo(criteria: dict[str, Any]) -> list[DemoListing]:
    rows = DEMO_LISTINGS[:]
    artists = [a.lower() for a in criteria.get("artists") or []]
    if artists:
        rows = [r for r in rows if any(a in r.artist.lower() or a in r.title_raw.lower() for a in artists)]
    if criteria.get("max_price") is not None:
        rows = [r for r in rows if r.price <= float(criteria["max_price"])]
    if criteria.get("year_start") is not None:
        rows = [r for r in rows if r.year is None or r.year >= int(criteria["year_start"])]
    if criteria.get("year_end") is not None:
        rows = [r for r in rows if r.year is None or r.year <= int(criteria["year_end"])]
    return rows
