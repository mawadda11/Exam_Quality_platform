"""Deterministic Arabic/English language detection for extraction routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TextLanguage(StrEnum):
    ARABIC = "arabic"
    ENGLISH = "english"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LanguageDetection:
    language: TextLanguage
    confidence: float
    arabic_letters: int
    latin_letters: int


def detect_text_language(text: str) -> LanguageDetection:
    arabic = sum(1 for char in text if "\u0600" <= char <= "\u06ff")
    latin = sum(1 for char in text if char.isascii() and char.isalpha())
    total = arabic + latin
    if total == 0:
        return LanguageDetection(TextLanguage.UNKNOWN, 0.0, arabic, latin)

    arabic_ratio = arabic / total
    latin_ratio = latin / total
    if arabic_ratio >= 0.8:
        language = TextLanguage.ARABIC
        confidence = arabic_ratio
    elif latin_ratio >= 0.8:
        language = TextLanguage.ENGLISH
        confidence = latin_ratio
    else:
        language = TextLanguage.MIXED
        # Mixed confidence increases as both scripts have meaningful presence.
        confidence = 1.0 - abs(arabic_ratio - latin_ratio)

    return LanguageDetection(language, round(confidence, 4), arabic, latin)


def combine_page_languages(detections: list[LanguageDetection]) -> LanguageDetection:
    arabic = sum(item.arabic_letters for item in detections)
    latin = sum(item.latin_letters for item in detections)
    return detect_text_language("ع" * arabic + "a" * latin)
