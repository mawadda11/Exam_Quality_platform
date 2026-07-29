"""Shared bilingual line-classification rules for exam text.

The classifier receives source text from either the digital or OCR path. It
normalizes only for matching and always returns the original line as the
record text, preserving source faithfulness for Extraction Review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto

from app.services.extraction.text_normalization import (
    normalize_arabic_for_matching,
    parse_localized_number,
)

# Public English pattern retained for existing callers/tests. The dedicated
# parser below accepts the broader approved bilingual label set while keeping
# the number semantically anchored to that label.
TOTAL_MARKS_PATTERN = re.compile(
    r"^Total\s+Marks\s*:\s*(\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)

_ENGLISH_QUESTION = re.compile(
    r"^Q\s*(\d+)(?:\.\s*|\s+\(\d+(?:\.\d+)?\)\s*:\s*|\s*:\s*)(.*)$",
    re.I,
)
_ARABIC_Q_QUESTION = re.compile(r"^س\s*(\d+)\s*(?:[\.:\-]\s*)?(.*)$")
_ARABIC_WORD_QUESTION = re.compile(r"^السؤال\s+(\d+|[\u0621-\u064a]+)\s*(?:[\.:\-]\s*)?(.*)$")

_ENGLISH_SUBQUESTION = re.compile(r"^\(?([a-z])\)?\s*[\).:\-]\s*(.*)$", re.I)
_ARABIC_SUBQUESTION = re.compile(r"^\(?([اأإآبجدهـوزحطيكلم نسعفصقرشتثخذضظغ])\)?\s*[\).:\-]\s*(.*)$")

_INSTRUCTIONS = re.compile(r"^(?:Instructions?|تعليمات|التعليمات)\s*:\s*", re.IGNORECASE)
_DECLARED_TOTAL_LABEL = re.compile(
    r"(?:"
    r"\b(?:Total\s+Marks?|Total\s+Score|Exam\s+Total|Maximum\s+Marks?)\b"
    r"|الدرجة\s+الكلية(?:\s+للاختبار)?"
    r"|إجمالي\s+الدرجات"
    r"|اجمالي\s+الدرجات"
    r"|مجموع\s+الدرجات"
    r"|المجموع\s+الكلي"
    r"|الدرجة\s+النهائية"
    r")",
    re.IGNORECASE,
)
_GENERIC_ENGLISH_TOTAL = re.compile(r"\bTotal\b", re.IGNORECASE)
_TOTAL_VALUE_AFTER_LABEL = re.compile(
    r"^\s*(?:[:=\-–—]\s*)?(?P<value>\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

_ENGLISH_MARKS = re.compile(r"[\[\(]\s*(\d+(?:\.\d+)?)\s*marks?\s*[\]\)]", re.IGNORECASE)
_ENGLISH_PREFIX_MARKS = re.compile(
    r"^Q\s*\d+\s+(?P<matched>\((?P<value>\d+(?:\.\d+)?)\))\s*:", re.IGNORECASE
)
_ARABIC_MARKS_BRACKET = re.compile(
    r"(?P<matched>[\[\(]\s*(?P<value>\d+(?:\.\d+)?)\s*(?:درجة|درجات|علامة|علامات)\s*[\]\)])"
)
_ARABIC_MARKS_PLAIN = re.compile(
    r"(?P<matched>(?P<value>\d+(?:\.\d+)?)\s*(?:درجة|درجات|علامة|علامات))\s*$"
)
_BARE_BRACKETED_MARKS = re.compile(r"(?P<matched>[\[\(]\s*(?P<value>\d+(?:\.\d+)?)\s*[\]\)])")

_ARABIC_ORDINALS: dict[str, int] = {
    "الاول": 1,
    "الأول": 1,
    "الاولى": 1,
    "الأولى": 1,
    "الثاني": 2,
    "الثانية": 2,
    "الثالث": 3,
    "الثالثة": 3,
    "الرابع": 4,
    "الرابعة": 4,
    "الخامس": 5,
    "الخامسة": 5,
    "السادس": 6,
    "السادسة": 6,
    "السابع": 7,
    "السابعة": 7,
    "الثامن": 8,
    "الثامنة": 8,
    "التاسع": 9,
    "التاسعة": 9,
    "العاشر": 10,
    "العاشرة": 10,
}

_ARABIC_SUBQUESTION_LABELS: dict[str, str] = {
    "ا": "a",
    "أ": "a",
    "إ": "a",
    "آ": "a",
    "ب": "b",
    "ج": "c",
    "د": "d",
    "ه": "e",
    "هـ": "e",
    "و": "f",
    "ز": "g",
    "ح": "h",
    "ط": "i",
    "ي": "j",
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
}


class LineKind(Enum):
    QUESTION = auto()
    SUBQUESTION = auto()
    INSTRUCTIONS = auto()
    TOTAL_MARKS = auto()
    OTHER = auto()


@dataclass(frozen=True)
class Marks:
    value: float
    matched_text: str


@dataclass(frozen=True)
class ClassifiedLine:
    kind: LineKind
    text: str
    number_label: str | None = None
    marks: Marks | None = None


def _question_number(token: str) -> int | None:
    if token.isdigit():
        return int(token)
    normalized = normalize_arabic_for_matching(token)
    return _ARABIC_ORDINALS.get(normalized)


def parse_marks(line: str) -> Marks | None:
    normalized = normalize_arabic_for_matching(line)

    match = _ENGLISH_MARKS.search(normalized)
    if match is not None:
        return Marks(value=parse_localized_number(match.group(1)), matched_text=match.group())

    prefix_match = _ENGLISH_PREFIX_MARKS.match(normalized)
    if prefix_match is not None:
        return Marks(
            value=parse_localized_number(prefix_match.group("value")),
            matched_text=prefix_match.group("matched"),
        )

    arabic_match = _ARABIC_MARKS_BRACKET.search(normalized) or _ARABIC_MARKS_PLAIN.search(
        normalized
    )
    if arabic_match is not None:
        # Preserve the original source fragment when practical. Localized digit
        # normalization does not change length, so the span remains aligned.
        start, end = arabic_match.span("matched")
        matched_text = line[start:end] if end <= len(line) else arabic_match.group("matched")
        return Marks(
            value=parse_localized_number(arabic_match.group("value")),
            matched_text=matched_text,
        )
    bare_match = _BARE_BRACKETED_MARKS.search(normalized)
    if bare_match is not None:
        start, end = bare_match.span("matched")
        matched_text = line[start:end] if end <= len(line) else bare_match.group("matched")
        return Marks(
            value=parse_localized_number(bare_match.group("value")),
            matched_text=matched_text,
        )
    return None


def parse_declared_total(line: str) -> float | None:
    normalized = normalize_arabic_for_matching(line)
    english = TOTAL_MARKS_PATTERN.match(normalized)
    if english is not None:
        return parse_localized_number(english.group(1))

    label = _DECLARED_TOTAL_LABEL.search(normalized)
    if label is None:
        label = _GENERIC_ENGLISH_TOTAL.search(normalized)
    if label is None:
        return None
    value = _TOTAL_VALUE_AFTER_LABEL.match(normalized[label.end() :])
    return parse_localized_number(value.group("value")) if value is not None else None


def has_declared_total_label(line: str) -> bool:
    """Return whether text contains an approved total-marks label.

    This is intentionally separate from numeric parsing so the layout-aware
    extractor can associate a label and value emitted as adjacent PDF lines.
    """

    normalized = normalize_arabic_for_matching(line)
    return (
        _DECLARED_TOTAL_LABEL.search(normalized) is not None
        or _GENERIC_ENGLISH_TOTAL.search(normalized) is not None
    )


def classify_line(line: str, current_parent_label: str | None) -> ClassifiedLine:
    """Classify one source line and return canonical, language-neutral labels."""

    normalized = normalize_arabic_for_matching(line)
    marks = parse_marks(line)

    question_match = _ENGLISH_QUESTION.match(normalized) or _ARABIC_Q_QUESTION.match(normalized)
    if question_match is not None:
        return ClassifiedLine(
            kind=LineKind.QUESTION,
            text=line,
            number_label=f"Q{int(question_match.group(1))}",
            marks=marks,
        )

    word_question = _ARABIC_WORD_QUESTION.match(normalized)
    if word_question is not None:
        number = _question_number(word_question.group(1))
        if number is not None:
            return ClassifiedLine(
                kind=LineKind.QUESTION,
                text=line,
                number_label=f"Q{number}",
                marks=marks,
            )

    subquestion_match = _ENGLISH_SUBQUESTION.match(normalized)
    if subquestion_match is not None:
        letter = subquestion_match.group(1).lower()
        label = f"{current_parent_label}({letter})" if current_parent_label else f"({letter})"
        return ClassifiedLine(kind=LineKind.SUBQUESTION, text=line, number_label=label, marks=marks)

    arabic_subquestion = _ARABIC_SUBQUESTION.match(normalized)
    if arabic_subquestion is not None:
        source_letter = arabic_subquestion.group(1)
        letter = _ARABIC_SUBQUESTION_LABELS.get(source_letter)
        if letter is not None:
            label = f"{current_parent_label}({letter})" if current_parent_label else f"({letter})"
            return ClassifiedLine(
                kind=LineKind.SUBQUESTION,
                text=line,
                number_label=label,
                marks=marks,
            )

    if _INSTRUCTIONS.match(normalized):
        return ClassifiedLine(kind=LineKind.INSTRUCTIONS, text=line)

    if parse_declared_total(line) is not None:
        return ClassifiedLine(kind=LineKind.TOTAL_MARKS, text=line)

    return ClassifiedLine(kind=LineKind.OTHER, text=line)
