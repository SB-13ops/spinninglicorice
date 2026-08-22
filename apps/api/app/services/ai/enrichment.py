"""Web-search-backed enrichment (uses Anthropic's server-side web_search tool).

Each of these makes real web searches (billed ~$10/1,000), so they are:
  * gated behind an explicit, user-initiated request (never bulk/automatic);
  * capped via ai_web_search_max_uses; and
  * gracefully no-op when the AI is disabled (return None).
"""
from __future__ import annotations

from app.services.ai.client import get_ai, ResearchResult

_SCOUT_SYSTEM = """You are a live-music concierge for a vinyl collector. Given a concert, \
use web search to briefly answer, in 2-3 sentences: is this a full-band performance or a \
solo/acoustic/DJ set, is the artist touring a specific album right now, and anything a fan \
who owns their records would want to know (notable support acts, tour name). Be concise and \
factual. If you can't verify something, say so rather than guessing."""

_PRESSING_SYSTEM = """You are a vinyl pressing expert. Given a specific record (title, artist, \
year, catalog number if provided), use web search to summarize in 2-4 sentences what makes this \
pressing notable to collectors: whether it's a first/original press, known variants or matrix \
details, and rough collector desirability. Be factual and cite sources; if unverifiable, say so."""


def enrich_concert(*, artist: str, event_name: str, venue: str | None, city: str | None) -> ResearchResult | None:
    ai = get_ai()
    if not ai.is_enabled:
        return None
    where = ", ".join([p for p in [venue, city] if p]) or "an unspecified venue"
    user = (
        f"Concert: {event_name} — {artist} at {where}. "
        f"Give a collector-focused briefing on this show."
    )
    return ai.research(_SCOUT_SYSTEM, user, max_tokens=700)


def research_pressing(
    *, title: str, artist: str | None = None, year: int | None = None, catalog_number: str | None = None
) -> ResearchResult | None:
    ai = get_ai()
    if not ai.is_enabled:
        return None
    bits = [f"Title: {title}"]
    if artist:
        bits.append(f"Artist: {artist}")
    if year:
        bits.append(f"Year: {year}")
    if catalog_number:
        bits.append(f"Catalog #: {catalog_number}")
    user = "Tell me about this vinyl pressing.\n" + "\n".join(bits)
    return ai.research(_PRESSING_SYSTEM, user, max_tokens=800)
