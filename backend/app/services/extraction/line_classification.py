"""Shared line-classification rules for exam text, regardless of whether that
text came from a digital PDF's native text layer (PdfPlumberExamExtractor's
original source) or from OCR of a rasterized scanned/image page (added
alongside it). Both sources ultimately produce lines of text that need the
exact same question/subquestion/instructions/total-marks detection - keeping
that detection in one place means a scanned exam and a digital exam are
classified by identical rules, rather than two regex sets that could drift.

This module only answers "what kind of line is this, and what data does it
carry" - it knows nothing about geometry, confidence, or PDFs/OCR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto

QUESTION_LINE = re.compile(r"^Q(\d+)\.\s*(.*)$")
SUBQUESTION_LINE = re.compile(r"^\(([a-z])\)\s*(.*)$")
INSTRUCTIONS_LINE = re.compile(r"^Instructions:\s*", re.IGNORECASE)
MARKS_ANYWHERE = re.compile(r"\[\s*(\d+(?:\.\d+)?)\s*marks?\s*\]", re.IGNORECASE)

# Public: M6's marks/total rule imports this to parse the same declared-total
# value back out of persisted evidence text, rather than redefining an
# equivalent pattern that could drift out of sync.
TOTAL_MARKS_PATTERN = re.compile(r"^Total\s+Marks\s*:\s*(\d+(?:\.\d+)?)\s*$", re.IGNORECASE)


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


def parse_marks(line: str) -> Marks | None:
    match = MARKS_ANYWHERE.search(line)
    if match is None:
        return None
    return Marks(value=float(match.group(1)), matched_text=match.group())


def classify_line(line: str, current_parent_label: str | None) -> ClassifiedLine:
    """Classifies one line of exam text. `current_parent_label` is the most
    recently seen top-level question's label (e.g. "Q2"), needed to build a
    subquestion's full label (e.g. "Q2(a)") - callers own tracking this
    across lines/pages since it's state, not something one line can know."""
    marks = parse_marks(line)

    question_match = QUESTION_LINE.match(line)
    if question_match:
        return ClassifiedLine(
            kind=LineKind.QUESTION,
            text=line,
            number_label=f"Q{question_match.group(1)}",
            marks=marks,
        )

    subquestion_match = SUBQUESTION_LINE.match(line)
    if subquestion_match:
        letter = subquestion_match.group(1)
        label = f"{current_parent_label}({letter})" if current_parent_label else f"({letter})"
        return ClassifiedLine(kind=LineKind.SUBQUESTION, text=line, number_label=label, marks=marks)

    if INSTRUCTIONS_LINE.match(line):
        return ClassifiedLine(kind=LineKind.INSTRUCTIONS, text=line)

    if TOTAL_MARKS_PATTERN.match(line):
        return ClassifiedLine(kind=LineKind.TOTAL_MARKS, text=line)

    return ClassifiedLine(kind=LineKind.OTHER, text=line)
