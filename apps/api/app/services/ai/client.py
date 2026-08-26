"""Central Anthropic (Claude) client for SpinningLicorice.

Every Claude call goes through here so we have one place to configure models,
cap cost, log, and — most importantly — degrade gracefully. If no API key is
set, `is_enabled` is False and callers fall back to their non-AI behavior; the
app never hard-depends on the AI being available.

Three entry points:
  * complete_json()  - structured extraction; returns a parsed dict or None.
  * complete_text()  - a short freeform completion; returns str or None.
  * research()       - a completion with Anthropic's server-side web_search
                       tool enabled; returns (text, citations) or None.
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger("spinninglicorice.ai")

# Stable server-side web search tool version.
WEB_SEARCH_TOOL_TYPE = "web_search_20250305"


@dataclass
class ResearchResult:
    text: str
    citations: list[dict] = field(default_factory=list)


class AIClient:
    def __init__(self) -> None:
        self._client = None
        if settings.anthropic_api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Anthropic client init failed: %s", exc)
                self._client = None

    @property
    def is_enabled(self) -> bool:
        return self._client is not None

    # -- structured JSON extraction ------------------------------------------
    def complete_json(self, system: str, user: str, *, max_tokens: int = 1024) -> dict | None:
        """Ask the fast model to return a JSON object; parse and return it.

        Returns None on any failure so callers can fall back. The prompt should
        instruct the model to return ONLY JSON.
        """
        text = self.complete_text(system, user, max_tokens=max_tokens)
        if text is None:
            return None
        return _extract_json(text)

    # -- short freeform text --------------------------------------------------
    def complete_text(self, system: str, user: str, *, max_tokens: int = 512) -> str | None:
        if not self.is_enabled:
            return None
        try:
            resp = self._client.messages.create(
                model=settings.ai_fast_model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return _first_text(resp)
        except Exception as exc:
            logger.warning("AI completion failed: %s", exc)
            return None

    # -- structured extraction from an image -----------------------------------
    def identify_image(
        self, system: str, user_text: str, image_bytes: bytes, media_type: str, *, max_tokens: int = 512
    ) -> dict | None:
        """Ask the fast model to look at a photo and return a JSON object.

        Used for record cover/label identification: less precise than a
        barcode scan, so callers should treat the result as a best guess to
        search with, not a confirmed match. Returns None on any failure
        (disabled, network error, unparseable response) so callers fall back
        to telling the person to try the barcode or add it by hand.
        """
        if not self.is_enabled:
            return None
        try:
            image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
            resp = self._client.messages.create(
                model=settings.ai_fast_model,
                max_tokens=max_tokens,
                system=system,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                            },
                            {"type": "text", "text": user_text},
                        ],
                    }
                ],
            )
            text = _first_text(resp)
            if text is None:
                return None
            return _extract_json(text)
        except Exception as exc:
            logger.warning("AI image identification failed: %s", exc)
            return None

    # -- web-search-backed research ------------------------------------------
    def research(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 1024,
        max_uses: int | None = None,
        allowed_domains: list[str] | None = None,
    ) -> ResearchResult | None:
        """Run a completion with the server-side web_search tool enabled.

        Each search is billed (~$10/1,000), so max_uses is capped by config.
        Returns the synthesized text plus any citations, or None on failure.
        """
        if not self.is_enabled:
            return None
        tool: dict = {
            "type": WEB_SEARCH_TOOL_TYPE,
            "name": "web_search",
            "max_uses": max_uses if max_uses is not None else settings.ai_web_search_max_uses,
        }
        if allowed_domains:
            tool["allowed_domains"] = allowed_domains
        try:
            resp = self._client.messages.create(
                model=settings.ai_research_model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=[tool],
            )
            return ResearchResult(text=_all_text(resp), citations=_collect_citations(resp))
        except Exception as exc:
            logger.warning("AI research failed: %s", exc)
            return None


def _first_text(resp) -> str | None:
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "text":
            return block.text
    return None


def _all_text(resp) -> str:
    parts = []
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def _collect_citations(resp) -> list[dict]:
    cites: list[dict] = []
    for block in getattr(resp, "content", []) or []:
        for c in getattr(block, "citations", None) or []:
            url = getattr(c, "url", None)
            title = getattr(c, "title", None)
            if url:
                cites.append({"url": url, "title": title})
    return cites


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON parse; tolerates ```json fences and surrounding prose."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    # Find the outermost object.
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        parsed = json.loads(t[start : end + 1])
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


# Process-wide singleton (constructed lazily).
_ai: AIClient | None = None


def get_ai() -> AIClient:
    global _ai
    if _ai is None:
        _ai = AIClient()
    return _ai
