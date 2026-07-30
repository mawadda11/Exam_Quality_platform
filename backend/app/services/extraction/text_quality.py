"""Mechanical quality gate for direct PDF text before OCR fallback."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextQuality:
    usable: bool
    confidence: float
    reason: str


def assess_text_quality(text: str) -> TextQuality:
    stripped = text.strip()
    if not stripped:
        return TextQuality(False, 0.0, "no_direct_text")

    non_space = [char for char in stripped if not char.isspace()]
    if not non_space:
        return TextQuality(False, 0.0, "no_direct_text")

    meaningful = sum(char.isalnum() or "\u0600" <= char <= "\u06ff" for char in non_space)
    replacement_count = stripped.count("\ufffd")
    control_count = sum(ord(char) < 32 and char not in "\n\r\t" for char in stripped)
    meaningful_ratio = meaningful / len(non_space)
    corruption_ratio = (replacement_count + control_count) / len(non_space)

    # A tiny amount of valid text (for example a page number) should not block
    # OCR on an otherwise scanned page.  Twenty meaningful characters is a
    # deliberately mechanical routing floor, not an academic threshold.
    enough_content = meaningful >= 20
    usable = enough_content and meaningful_ratio >= 0.45 and corruption_ratio <= 0.05
    confidence = max(0.0, min(1.0, meaningful_ratio * (1.0 - corruption_ratio)))
    reason = "usable_direct_text" if usable else "low_quality_direct_text"
    return TextQuality(usable, round(confidence, 4), reason)
