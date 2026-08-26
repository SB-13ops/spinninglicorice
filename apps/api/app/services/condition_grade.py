"""Suggest a rough condition grade from a photo of a record's cover, jacket,
or label — deliberately scoped to what a photo can actually show.

This does NOT grade the vinyl playing surface. Real media-condition grading
requires tilting the record under angled light to catch fine hairline
scratches; a flat photo cannot reveal that, even for an experienced human
grader. So this only ever comments on what's visibly in the photo (the
cover/jacket/label itself), and the prompt explicitly refuses to claim
anything about the actual groove/playing condition. The result is a
suggestion for the person to confirm or override, never an authoritative
grade — condition affects real value, so overconfidence here would be a
genuine disservice.
"""
from __future__ import annotations

from app.services.ai.client import AIClient

_VALID_GRADES = {
    "Mint (M)",
    "Near Mint (NM or M-)",
    "Very Good Plus (VG+)",
    "Very Good (VG)",
    "Good Plus (G+)",
    "Good (G)",
    "Fair (F)",
    "Poor (P)",
}

_SYSTEM = """You are looking at a single photo of a vinyl record's cover, jacket, or its \
printed center label. Assess ONLY the visible physical condition of what's shown in the \
photo -- you cannot judge the vinyl's actual playing surface or groove condition from a \
cover or label photo, so never claim to. Real grooves need to be tilted under angled light \
to check for hairline scratches, which a flat photo can't show.

Respond with ONLY a JSON object, no other text, in exactly this shape:
{"suggested_grade": one of "Mint (M)", "Near Mint (NM or M-)", "Very Good Plus (VG+)", "Very Good (VG)", "Good Plus (G+)", "Good (G)", "Fair (F)", "Poor (P)", or null,
 "observations": string,
 "confidence": "high" | "medium" | "low"}

Rules:
- Base the grade only on what's visible: seam splits, ring wear, corner or edge wear, writing, stickers, tears, discoloration, water damage, spindle marks.
- If the photo doesn't show enough to judge (blurry, too dark, too cropped, or it isn't a cover/label at all), set suggested_grade to null and say why in observations.
- When genuinely between two grades, pick the more conservative (lower) one, and say so.
- Keep observations to one or two short, specific sentences naming what you actually see."""

_USER_TEXT = (
    "Assess the visible condition of the cover/jacket/label in this photo. "
    "Respond with only the JSON object described in the system prompt."
)


def suggest_condition(image_bytes: bytes, media_type: str) -> dict:
    """Returns {"suggested_grade": str|None, "observations": str, "confidence": str}.

    Raises RuntimeError if AI isn't configured or the call fails outright.
    """
    ai = AIClient()
    if not ai.is_enabled:
        raise RuntimeError("Condition suggestions aren't available on this server yet.")

    result = ai.identify_image(_SYSTEM, _USER_TEXT, image_bytes, media_type)
    if not result:
        raise RuntimeError("Couldn't reach the condition assessment service. Please try again.")

    grade = result.get("suggested_grade")
    if grade not in _VALID_GRADES:
        grade = None  # guard against the model returning something off-menu

    return {
        "suggested_grade": grade,
        "observations": result.get("observations") or "",
        "confidence": result.get("confidence") or "low",
    }
