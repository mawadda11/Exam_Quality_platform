"""Digital, text-based exam PDF extractor.

Reads only a PDF's existing text layer via pdfplumber - it never performs OCR.
A page with no extractable text (e.g. a scanned image) simply yields no
questions for that page; scanned-exam support is a separate, later milestone.

Parsing is a deterministic, regex-based heuristic, not a statistical model:
- a line matching "Q<n>." starts a new top-level question;
- a line matching "(<letter>)" is a child of the most recently seen
  top-level question;
- a "[<n> marks]" bracket anywhere in a line attaches marks to that line;
- a line starting with "Instructions:" becomes non-question evidence;
- a line matching "Total Marks: <n>" becomes declared-total evidence (not a
  question) - TOTAL_MARKS_PATTERN is exported so rule code (M6) can parse the
  same value back out of the persisted evidence text without redefining it.
Confidence reflects whether the text match and the position (geometry) match
agreed, not any statistical certainty.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber

from app.services.extraction.types import (
    ExtractedEvidence,
    ExtractedQuestion,
    ExtractionError,
    ExtractionResult,
    Geometry,
)

_QUESTION_LINE = re.compile(r"^Q(\d+)\.\s*(.*)$")
_SUBQUESTION_LINE = re.compile(r"^\(([a-z])\)\s*(.*)$")
_INSTRUCTIONS_LINE = re.compile(r"^Instructions:\s*", re.IGNORECASE)
_MARKS_ANYWHERE = re.compile(r"\[\s*(\d+(?:\.\d+)?)\s*marks?\s*\]", re.IGNORECASE)

# Public (no leading underscore): M6's marks/total rule imports this to parse
# the same declared-total value back out of the persisted evidence text,
# rather than redefining an equivalent pattern that could drift out of sync.
TOTAL_MARKS_PATTERN = re.compile(r"^Total\s+Marks\s*:\s*(\d+(?:\.\d+)?)\s*$", re.IGNORECASE)

_QUESTION_SEARCH = r"Q\d+\."
_SUBQUESTION_SEARCH = r"\([a-z]\)"
_MARKS_SEARCH = r"\[\s*\d+(?:\.\d+)?\s*marks?\s*\]"
_INSTRUCTIONS_SEARCH = r"Instructions:"
_TOTAL_MARKS_SEARCH = r"Total\s+Marks\s*:\s*\d+(?:\.\d+)?"

_FULL_CONFIDENCE = 1.0
_NO_GEOMETRY_CONFIDENCE = 0.6


@dataclass(frozen=True)
class _Marks:
    value: float
    matched_text: str


def _parse_marks(line: str) -> _Marks | None:
    match = _MARKS_ANYWHERE.search(line)
    if match is None:
        return None
    return _Marks(value=float(match.group(1)), matched_text=match.group())


def _geometry_from_match(match: dict[str, Any]) -> Geometry:
    return Geometry(
        x0=float(match["x0"]),
        top=float(match["top"]),
        x1=float(match["x1"]),
        bottom=float(match["bottom"]),
    )


def _next_geometry(matches: Iterator[dict[str, Any]]) -> Geometry | None:
    match = next(matches, None)
    return _geometry_from_match(match) if match is not None else None


def _confidence_for(geometry: Geometry | None) -> float:
    return _FULL_CONFIDENCE if geometry is not None else _NO_GEOMETRY_CONFIDENCE


class PdfPlumberExamExtractor:
    """Digital-PDF-only exam extractor. See module docstring for the heuristic."""

    def extract(self, pdf_path: Path) -> ExtractionResult:
        try:
            return self._extract(pdf_path)
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError(f"Failed to parse digital PDF: {pdf_path.name}") from exc

    def _extract(self, pdf_path: Path) -> ExtractionResult:
        questions: list[ExtractedQuestion] = []
        evidence: list[ExtractedEvidence] = []
        sequence = 0
        current_parent_label: str | None = None

        with pdfplumber.open(pdf_path) as document:
            for page_index, page in enumerate(document.pages):
                page_number = page_index + 1
                text = page.extract_text() or ""
                lines = [line.strip() for line in text.splitlines() if line.strip()]

                question_matches = iter(page.search(_QUESTION_SEARCH))
                subquestion_matches = iter(page.search(_SUBQUESTION_SEARCH))
                marks_matches = iter(page.search(_MARKS_SEARCH))
                instructions_matches = iter(page.search(_INSTRUCTIONS_SEARCH))
                total_marks_matches = iter(page.search(_TOTAL_MARKS_SEARCH))

                for line in lines:
                    marks = _parse_marks(line)
                    marks_geometry = _next_geometry(marks_matches) if marks else None

                    question_match = _QUESTION_LINE.match(line)
                    subquestion_match = _SUBQUESTION_LINE.match(line)

                    if question_match:
                        number_label = f"Q{question_match.group(1)}"
                        geometry = _next_geometry(question_matches)
                        current_parent_label = number_label
                    elif subquestion_match:
                        letter = subquestion_match.group(1)
                        number_label = (
                            f"{current_parent_label}({letter})"
                            if current_parent_label
                            else f"({letter})"
                        )
                        geometry = _next_geometry(subquestion_matches)
                    elif _INSTRUCTIONS_LINE.match(line):
                        geometry = _next_geometry(instructions_matches)
                        evidence.append(
                            ExtractedEvidence(
                                evidence_type="instructions",
                                page_number=page_number,
                                item_reference="instructions",
                                extracted_text=line,
                                confidence=_confidence_for(geometry),
                                geometry=geometry,
                                question_number_label=None,
                            )
                        )
                        continue
                    elif TOTAL_MARKS_PATTERN.match(line):
                        geometry = _next_geometry(total_marks_matches)
                        evidence.append(
                            ExtractedEvidence(
                                evidence_type="declared_total",
                                page_number=page_number,
                                item_reference="total",
                                extracted_text=line,
                                confidence=_confidence_for(geometry),
                                geometry=geometry,
                                question_number_label=None,
                            )
                        )
                        continue
                    else:
                        continue

                    sequence += 1
                    questions.append(
                        ExtractedQuestion(
                            number_label=number_label,
                            text=line,
                            page_number=page_number,
                            parent_number_label=(
                                current_parent_label if subquestion_match else None
                            ),
                            marks=marks.value if marks else None,
                            sequence=sequence,
                            confidence=_confidence_for(geometry),
                            geometry=geometry,
                        )
                    )
                    evidence.append(
                        ExtractedEvidence(
                            evidence_type="question_text",
                            page_number=page_number,
                            item_reference=number_label,
                            extracted_text=line,
                            confidence=_confidence_for(geometry),
                            geometry=geometry,
                            question_number_label=number_label,
                        )
                    )
                    if marks is not None:
                        evidence.append(
                            ExtractedEvidence(
                                evidence_type="marks",
                                page_number=page_number,
                                item_reference=number_label,
                                extracted_text=marks.matched_text,
                                confidence=_confidence_for(marks_geometry),
                                geometry=marks_geometry,
                                question_number_label=number_label,
                            )
                        )

        return ExtractionResult(questions=questions, evidence=evidence)
