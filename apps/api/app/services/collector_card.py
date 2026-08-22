"""Shareable "Collector Card" — a good-looking SVG summarizing a collection.

Pulls together the Collector DNA (top genres, era), a rarity score, and the
current estimated worth into a single card image the owner can share. Rendered
as SVG so it needs no image libraries and stays crisp at any size; the frontend
can display it directly or convert to PNG for social posts.

A public, tokenized variant can be served without auth (reusing the account
public-share token) so a shared card link works for anyone.
"""
from __future__ import annotations

import html
import uuid

from sqlalchemy.orm import Session

from app.services.collector_dna import CollectorDNAService
from app.services.valuation import get_value_summary


# Palette matches the app's warm "vinyl" theme.
_BG = "#15120e"
_BG2 = "#0e0d0a"
_GOLD = "#d09b4c"
_CREAM = "#eee0c2"
_MUTED = "#b4a48b"
_LINE = "#49371f"


def _rarity_score(dna: dict, value_summary: dict) -> tuple[int, str]:
    """A light 0–100 'rarity/heat' score from era spread, price band, and size.
    Deterministic and explainable — not a market appraisal."""
    score = 0
    music = dna.get("music_dna", {}) if dna else {}
    collector = dna.get("collector_dna", {}) if dna else {}

    span = music.get("year_span") or {}
    if span.get("start") and span.get("end"):
        breadth = min(span["end"] - span["start"], 60)
        score += int(breadth / 60 * 30)  # up to 30 for era breadth

    band = collector.get("typical_price_range") or {}
    if band.get("high"):
        score += min(int(band["high"] / 5), 35)  # up to 35 for price band

    count = value_summary.get("item_count", 0)
    score += min(int(count / 10), 35)  # up to 35 for size

    score = max(0, min(100, score))
    if score >= 75:
        label = "Deep Crate"
    elif score >= 50:
        label = "Serious Digger"
    elif score >= 25:
        label = "Building Nicely"
    else:
        label = "Just Getting Started"
    return score, label


def build_collector_card(db: Session, user_id: uuid.UUID, *, display_name: str | None = None) -> str:
    dna = CollectorDNAService(db).get(user_id=user_id) or {}
    value = get_value_summary(db, user_id)

    music = dna.get("music_dna", {})
    top_artists = [a.get("name") for a in (music.get("top_artists") or [])][:3]
    # DNA tracks labels, not genres — use labels as the "sound/style" signal.
    top_genres = [g.get("name") if isinstance(g, dict) else g for g in (music.get("top_labels") or [])][:3]
    span = music.get("year_span") or {}
    era = f"{span['start']}–{span['end']}" if span.get("start") and span.get("end") else "—"

    score, tier = _rarity_score(dna, value)
    worth = value.get("total_value") or 0
    count = value.get("item_count") or 0

    name = html.escape(display_name or "A Burnt Jacket Collector")
    genres_txt = html.escape(", ".join(top_genres) or "Eclectic")
    artists_txt = html.escape(", ".join(top_artists) or "—")

    # 1200x630 — standard social share dimensions.
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{_BG}"/>
      <stop offset="1" stop-color="{_BG2}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.35" r="0.7">
      <stop offset="0" stop-color="{_GOLD}" stop-opacity="0.16"/>
      <stop offset="1" stop-color="{_GOLD}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect width="1200" height="630" fill="url(#glow)"/>
  <rect x="24" y="24" width="1152" height="582" rx="20" fill="none" stroke="{_LINE}" stroke-width="2"/>

  <!-- vinyl mark -->
  <circle cx="980" cy="150" r="92" fill="#1a1510" stroke="{_LINE}" stroke-width="2"/>
  <circle cx="980" cy="150" r="30" fill="{_GOLD}"/>
  <circle cx="980" cy="150" r="8" fill="{_BG}"/>

  <text x="70" y="120" font-family="Georgia, serif" font-size="30" fill="{_GOLD}" font-weight="bold" letter-spacing="2">BURNT JACKET</text>
  <text x="70" y="185" font-family="Georgia, serif" font-size="56" fill="{_CREAM}" font-weight="bold">{name}</text>
  <text x="70" y="225" font-family="Arial, sans-serif" font-size="24" fill="{_MUTED}">{tier} · Rarity {score}/100</text>

  <!-- stats grid -->
  <g font-family="Arial, sans-serif">
    <text x="70" y="330" font-size="20" fill="{_MUTED}">RECORDS</text>
    <text x="70" y="378" font-size="52" fill="{_CREAM}" font-weight="bold">{count}</text>

    <text x="360" y="330" font-size="20" fill="{_MUTED}">EST. WORTH</text>
    <text x="360" y="378" font-size="52" fill="{_GOLD}" font-weight="bold">${worth:,.0f}</text>

    <text x="720" y="330" font-size="20" fill="{_MUTED}">ERA</text>
    <text x="720" y="378" font-size="52" fill="{_CREAM}" font-weight="bold">{era}</text>
  </g>

  <line x1="70" y1="430" x2="1130" y2="430" stroke="{_LINE}" stroke-width="1"/>

  <g font-family="Arial, sans-serif">
    <text x="70" y="480" font-size="20" fill="{_MUTED}">TOP LABELS</text>
    <text x="70" y="516" font-size="30" fill="{_CREAM}">{genres_txt}</text>

    <text x="70" y="562" font-size="20" fill="{_MUTED}">MOST COLLECTED</text>
    <text x="70" y="596" font-size="30" fill="{_CREAM}">{artists_txt}</text>
  </g>
</svg>"""
