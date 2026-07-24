"""Exam PDF extractor: reads a PDF's native text layer via pdfplumber where
one exists, and falls back to OCR (Tesseract, via app.services.extraction.ocr)
for any page that yields no extractable text at all (e.g. a scanned image) -
the only non-invented, mechanical signal available for "this page needs OCR".
Native-text pages never go through OCR, keeping today's proven digital
behavior and its confidence semantics completely unchanged.

Parsing is a deterministic, regex-based heuristic, not a statistical model -
see app.services.extraction.line_classification for the actual rules (shared
between the digital and OCR paths, so a scanned exam and a digital exam are
classified identically):
- a line matching "Q<n>." starts a new top-level question;
- a line matching "(<letter>)" is a child of the most recently seen
  top-level question;
- a "[<n> marks]" bracket anywhere in a line attaches marks to that line;
- a line starting with "Instructions:" becomes non-question evidence;
- a line matching "Total Marks: <n>" becomes declared-total evidence.

Confidence means different things per source: for a digitally-extracted line
it reflects whether the text match and the position (geometry) match agreed,
not statistical certainty; for an OCR-extracted line it's Tesseract's own
recognition confidence, converted from its 0-100 scale to 0.0-1.0. Both are
stored in the same `confidence: float` column - callers should not assume
the two are numerically comparable.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pdfplumber
from pdfplumber.page import Page

# TOTAL_MARKS_PATTERN is unused in this file but re-exported - app.services.
# rules.marks_total imports it from here (not from line_classification
# directly) to parse the same declared-total value back out of persisted
# evidence text, without redefining an equivalent pattern that could drift
# out of sync. The `as TOTAL_MARKS_PATTERN` re-import (rather than a plain
# import) is mypy's required idiom for an intentional re-export under strict
# mode's implicit-reexport check.
from app.services.extraction.line_classification import (
    TOTAL_MARKS_PATTERN as TOTAL_MARKS_PATTERN,
)
from app.services.extraction.line_classification import (
    ClassifiedLine,
    LineKind,
    Marks,
    classify_line,
)
from app.services.extraction.ocr import OCR_RESOLUTION_DPI, OcrEngine, TesseractOcrEngine
from app.services.extraction.types import (
    ExtractedEvidence,
    ExtractedQuestion,
    ExtractionError,
    ExtractionResult,
    Geometry,
)

_QUESTION_SEARCH = r"Q\d+\."
_SUBQUESTION_SEARCH = r"\([a-z]\)"
_MARKS_SEARCH = r"\[\s*\d+(?:\.\d+)?\s*marks?\s*\]"
_INSTRUCTIONS_SEARCH = r"Instructions:"
_TOTAL_MARKS_SEARCH = r"Total\s+Marks\s*:\s*\d+(?:\.\d+)?"

_FULL_CONFIDENCE = 1.0
_NO_GEOMETRY_CONFIDENCE = 0.6


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
    """Digital-first, OCR-fallback exam extractor. See module docstring."""

    def __init__(self, ocr_engine: OcrEngine | None = None) -> None:
        self._ocr_engine = ocr_engine or TesseractOcrEngine()

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

                if lines:
                    sequence, current_parent_label = self._process_digital_page(
                        page,
                        lines,
                        page_number,
                        sequence,
                        current_parent_label,
                        questions,
                        evidence,
                    )
                else:
                    sequence, current_parent_label = self._process_ocr_page(
                        page, page_number, sequence, current_parent_label, questions, evidence
                    )

        return ExtractionResult(questions=questions, evidence=evidence)

    def _process_digital_page(
        self,
        page: Page,
        lines: list[str],
        page_number: int,
        sequence: int,
        current_parent_label: str | None,
        questions: list[ExtractedQuestion],
        evidence: list[ExtractedEvidence],
    ) -> tuple[int, str | None]:
        question_matches = iter(page.search(_QUESTION_SEARCH))
        subquestion_matches = iter(page.search(_SUBQUESTION_SEARCH))
        marks_matches = iter(page.search(_MARKS_SEARCH))
        instructions_matches = iter(page.search(_INSTRUCTIONS_SEARCH))
        total_marks_matches = iter(page.search(_TOTAL_MARKS_SEARCH))

        for line in lines:
            classified = classify_line(line, current_parent_label)
            marks_geometry = _next_geometry(marks_matches) if classified.marks else None

            if classified.kind is LineKind.QUESTION:
                geometry = _next_geometry(question_matches)
            elif classified.kind is LineKind.SUBQUESTION:
                geometry = _next_geometry(subquestion_matches)
            elif classified.kind is LineKind.INSTRUCTIONS:
                geometry = _next_geometry(instructions_matches)
            elif classified.kind is LineKind.TOTAL_MARKS:
                geometry = _next_geometry(total_marks_matches)
            else:
                continue

            sequence, current_parent_label = self._emit(
                classified,
                geometry,
                _confidence_for(geometry),
                marks_geometry,
                _confidence_for(marks_geometry),
                page_number,
                sequence,
                current_parent_label,
                questions,
                evidence,
            )

        return sequence, current_parent_label

    def _process_ocr_page(
        self,
        page: Page,
        page_number: int,
        sequence: int,
        current_parent_label: str | None,
        questions: list[ExtractedQuestion],
        evidence: list[ExtractedEvidence],
    ) -> tuple[int, str | None]:
        scale = OCR_RESOLUTION_DPI / 72.0
        image = page.to_image(resolution=OCR_RESOLUTION_DPI).original
        ocr_lines = self._ocr_engine.lines_for_image(image, scale)

        for ocr_line in ocr_lines:
            classified = classify_line(ocr_line.text, current_parent_label)
            if classified.kind is LineKind.OTHER:
                continue

            # OCR gives one recognized geometry/confidence per whole line -
            # unlike the digital path, there's no separate "just the marks
            # bracket" position to look up, so a marks evidence row reuses
            # the same line-level geometry/confidence as its parent line.
            sequence, current_parent_label = self._emit(
                classified,
                ocr_line.geometry,
                ocr_line.confidence,
                ocr_line.geometry,
                ocr_line.confidence,
                page_number,
                sequence,
                current_parent_label,
                questions,
                evidence,
            )

        return sequence, current_parent_label

    def _emit(
        self,
        classified: ClassifiedLine,
        geometry: Geometry | None,
        confidence: float,
        marks_geometry: Geometry | None,
        marks_confidence: float,
        page_number: int,
        sequence: int,
        current_parent_label: str | None,
        questions: list[ExtractedQuestion],
        evidence: list[ExtractedEvidence],
    ) -> tuple[int, str | None]:
        """Shared row-construction, identical regardless of whether `classified`
        came from a digital line or an OCR line - the only difference between
        the two paths is how geometry/confidence were sourced above."""
        marks: Marks | None = classified.marks

        if classified.kind is LineKind.INSTRUCTIONS:
            evidence.append(
                ExtractedEvidence(
                    evidence_type="instructions",
                    page_number=page_number,
                    item_reference="instructions",
                    extracted_text=classified.text,
                    confidence=confidence,
                    geometry=geometry,
                    question_number_label=None,
                )
            )
            return sequence, current_parent_label

        if classified.kind is LineKind.TOTAL_MARKS:
            evidence.append(
                ExtractedEvidence(
                    evidence_type="declared_total",
                    page_number=page_number,
                    item_reference="total",
                    extracted_text=classified.text,
                    confidence=confidence,
                    geometry=geometry,
                    question_number_label=None,
                )
            )
            return sequence, current_parent_label

        # QUESTION or SUBQUESTION from here on.
        number_label = classified.number_label
        assert number_label is not None  # classify_line always sets it for these two kinds
        if classified.kind is LineKind.QUESTION:
            current_parent_label = number_label

        sequence += 1
        questions.append(
            ExtractedQuestion(
                number_label=number_label,
                text=classified.text,
                page_number=page_number,
                parent_number_label=(
                    current_parent_label if classified.kind is LineKind.SUBQUESTION else None
                ),
                marks=marks.value if marks else None,
                sequence=sequence,
                confidence=confidence,
                geometry=geometry,
            )
        )
        evidence.append(
            ExtractedEvidence(
                evidence_type="question_text",
                page_number=page_number,
                item_reference=number_label,
                extracted_text=classified.text,
                confidence=confidence,
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
                    confidence=marks_confidence,
                    geometry=marks_geometry,
                    question_number_label=number_label,
                )
            )

        return sequence, current_parent_label
