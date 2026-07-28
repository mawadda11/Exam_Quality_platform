"""Digital-first bilingual exam extraction with page-level OCR fallback.

The source PDF text is attempted first. A mechanical quality gate decides
whether that page is usable; empty or clearly garbled pages are rasterized and
sent through the configured OCR adapter. Arabic/English matching happens only
in the line classifier, while persisted question/evidence text remains exactly
the source line returned by the digital or OCR provider.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber
from pdfplumber.page import Page

from app.services.extraction.language_detection import (
    LanguageDetection,
    combine_page_languages,
    detect_text_language,
)
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
from app.services.extraction.text_quality import assess_text_quality
from app.services.extraction.types import (
    ExtractedEvidence,
    ExtractedQuestion,
    ExtractionError,
    ExtractionResult,
    Geometry,
    PageExtractionDiagnostic,
)

_FULL_CONFIDENCE = 1.0
_NO_GEOMETRY_CONFIDENCE = 0.6
_LOW_CONFIDENCE_REVIEW = 0.75


def _geometry_from_match(match: dict[str, Any]) -> Geometry:
    return Geometry(
        x0=float(match["x0"]),
        top=float(match["top"]),
        x1=float(match["x1"]),
        bottom=float(match["bottom"]),
    )


def _geometry_for_text(page: Page, text: str) -> Geometry | None:
    """Find the first exact source-text occurrence on a digital page.

    Exact escaped lookup supports English and Arabic without maintaining a
    second language-specific geometry regex. Geometry is traceability data;
    failure to locate it lowers confidence but never invents coordinates.
    """

    if not text:
        return None
    try:
        matches = page.search(re.escape(text))
    except Exception:
        return None
    return _geometry_from_match(matches[0]) if matches else None


def _confidence_for(geometry: Geometry | None) -> float:
    return _FULL_CONFIDENCE if geometry is not None else _NO_GEOMETRY_CONFIDENCE


class PdfPlumberExamExtractor:
    """Extract digital, Arabic, English, mixed, and scanned exam pages."""

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
        diagnostics: list[PageExtractionDiagnostic] = []
        detections: list[LanguageDetection] = []
        sequence = 0
        current_parent_label: str | None = None

        with pdfplumber.open(pdf_path) as document:
            for page_index, page in enumerate(document.pages):
                page_number = page_index + 1
                text = page.extract_text() or ""
                quality = assess_text_quality(text)

                if quality.usable:
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    detection = detect_text_language(text)
                    detections.append(detection)
                    diagnostics.append(
                        PageExtractionDiagnostic(
                            page_number=page_number,
                            language=detection.language,
                            language_confidence=detection.confidence,
                            extraction_method="direct_text",
                            text_quality_confidence=quality.confidence,
                            review_recommended=False,
                            reason=quality.reason,
                        )
                    )
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
                    sequence, current_parent_label, detection, average_confidence = (
                        self._process_ocr_page(
                            page,
                            page_number,
                            sequence,
                            current_parent_label,
                            questions,
                            evidence,
                        )
                    )
                    detections.append(detection)
                    diagnostics.append(
                        PageExtractionDiagnostic(
                            page_number=page_number,
                            language=detection.language,
                            language_confidence=detection.confidence,
                            extraction_method="ocr",
                            text_quality_confidence=average_confidence,
                            review_recommended=average_confidence < _LOW_CONFIDENCE_REVIEW,
                            reason=quality.reason,
                        )
                    )

        document_language = combine_page_languages(detections).language
        return ExtractionResult(
            questions=questions,
            evidence=evidence,
            document_language=document_language,
            page_diagnostics=diagnostics,
        )

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
        for line in lines:
            classified = classify_line(line, current_parent_label)
            if classified.kind is LineKind.OTHER:
                continue

            geometry = _geometry_for_text(page, line)
            marks_geometry = (
                _geometry_for_text(page, classified.marks.matched_text)
                if classified.marks is not None
                else None
            )
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
    ) -> tuple[int, str | None, LanguageDetection, float]:
        scale = OCR_RESOLUTION_DPI / 72.0
        image = page.to_image(resolution=OCR_RESOLUTION_DPI).original
        ocr_lines = self._ocr_engine.lines_for_image(image, scale)

        for ocr_line in ocr_lines:
            classified = classify_line(ocr_line.text, current_parent_label)
            if classified.kind is LineKind.OTHER:
                continue
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

        joined_text = "\n".join(line.text for line in ocr_lines)
        detection = detect_text_language(joined_text)
        average_confidence = (
            sum(line.confidence for line in ocr_lines) / len(ocr_lines) if ocr_lines else 0.0
        )
        return sequence, current_parent_label, detection, round(average_confidence, 4)

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

        number_label = classified.number_label
        assert number_label is not None
        parent_label = current_parent_label if classified.kind is LineKind.SUBQUESTION else None
        if classified.kind is LineKind.QUESTION:
            current_parent_label = number_label

        sequence += 1
        questions.append(
            ExtractedQuestion(
                number_label=number_label,
                text=classified.text,
                page_number=page_number,
                parent_number_label=parent_label,
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
