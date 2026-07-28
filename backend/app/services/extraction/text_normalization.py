"""Source-safe normalization helpers for Arabic/English extraction.

The extractor always persists the original source text.  These helpers are
used only for deterministic matching, digit parsing, and language-neutral
question labels.  They must never be used to silently rewrite the evidence
shown to a reviewer.
"""

from __future__ import annotations

import re
import unicodedata

_ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_EASTERN_ARABIC_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ASCII_DIGITS = "0123456789"
_DIGIT_TRANSLATION = str.maketrans(
    _ARABIC_INDIC_DIGITS + _EASTERN_ARABIC_DIGITS,
    _ASCII_DIGITS + _ASCII_DIGITS,
)

# Arabic combining marks, Quranic annotation marks, and tatweel.  Removing
# these for matching makes headings such as "التَّعليمات" deterministic while
# preserving the untouched source string in the extracted record.
_ARABIC_MARKS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
_WHITESPACE = re.compile(r"\s+")


def to_ascii_digits(value: str) -> str:
    """Convert Arabic-Indic and Eastern Arabic digits to ASCII digits."""

    return value.translate(_DIGIT_TRANSLATION)


def normalize_arabic_for_matching(value: str) -> str:
    """Return a conservative normalized form used only by parser regexes.

    Normalization intentionally avoids broad letter folding (for example,
    turning every hamza into a bare alif) because that can change source
    meaning.  It performs Unicode compatibility normalization, digit
    conversion, Arabic punctuation normalization, diacritic/tatweel removal,
    and whitespace compaction.
    """

    normalized = unicodedata.normalize("NFKC", value)
    normalized = to_ascii_digits(normalized)
    normalized = _ARABIC_MARKS.sub("", normalized)
    normalized = normalized.replace("،", ",").replace("؛", ";").replace("：", ":")
    normalized = normalized.replace("٪", "%")
    return _WHITESPACE.sub(" ", normalized).strip()


def parse_localized_number(value: str) -> float:
    """Parse a decimal number written with English or Arabic digits."""

    normalized = normalize_arabic_for_matching(value).replace(",", "")
    return float(normalized)
