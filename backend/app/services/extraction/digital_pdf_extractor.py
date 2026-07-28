"""Digital-first bilingual exam extraction with page-level OCR fallback.

The source PDF text is attempted first. A mechanical quality gate decides
whether that page is usable; empty or clearly garbled pages are rasterized and
sent through the configured OCR adapter. Arabic/English matching happens only
in the line classifier, while persisted question/evidence text remains exactly
the source line returned by the digital or OCR provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
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
from app.services.extraction.pdf_layout import PdfLayoutLine, extract_layout_lines
from app.services.extraction.structured_evidence import (
    extract_page_materials,
    extract_question_references,
)
from app.services.extraction.text_quality import assess_text_quality
from app.services.extraction.types import (
    ExtractedDocumentReference,
    ExtractedEvidence,
    ExtractedQuestion,
    ExtractedSupportingAnnotation,
    ExtractedSupportingMaterial,
    ExtractionError,
    ExtractionResult,
    Geometry,
    PageExtractionDiagnostic,
)

_FULL_CONFIDENCE = 1.0
_NO_GEOMETRY_CONFIDENCE = 0.6
_LOW_CONFIDENCE_REVIEW = 0.75
_STEM_VERTICAL_GAP = 35.0


@dataclass
class _QuestionDraft:
    classified: ClassifiedLine
    page_number: int
    parent_number_label: str | None
    reading_parts: list[str]
    raw_parts: list[str]
    geometries: list[Geometry]
    marks_geometry: Geometry | None


def _union_geometry(geometries: list[Geometry]) -> Geometry | None:
    if not geometries:
        return None
    return Geometry(
        min(item.x0 for item in geometries),
        min(item.top for item in geometries),
        max(item.x1 for item in geometries),
        max(item.bottom for item in geometries),
    )


def _joined_stem(parts: list[str]) -> str:
    value = " ".join(part.strip() for part in parts if part.strip())
    value = re.sub(r"(\d)\.\s+and\b", r"\1 and", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\b(Using\s+(?:Table|Figure|Code)\s+\d+)\s+",
        r"\1, ",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r",\s*\.\s+average\b", " average.", value, flags=re.IGNORECASE)
    value = re.sub(r"\((\d+)\)Code\b", r"(Code \1)", value)
    value = re.sub(r"([\u0600-\u06ff])\s+ة\b", r"\1ة", value)
    value = re.sub(r"\s+([,.;:!?،؛])", r"\1", value)
    return value.strip()


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
        supporting_materials: list[ExtractedSupportingMaterial] = []
        supporting_annotations: list[ExtractedSupportingAnnotation] = []
        sequence = 0
        current_parent_label: str | None = None

        with pdfplumber.open(pdf_path) as document:
            for page_index, page in enumerate(document.pages):
                page_number = page_index + 1
                text = page.extract_text() or ""
                quality = assess_text_quality(text)

                if quality.usable:
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    layout_lines = extract_layout_lines(page, page_number=page_number)
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
                    structured = extract_page_materials(
                        page,
                        layout_lines or lines,
                        page_number=page_number,
                        extraction_method="direct_text",
                    )
                    supporting_materials.extend(structured.materials)
                    supporting_annotations.extend(structured.annotations)
                    if any(
                        classify_line(line, current_parent_label).kind
                        in {LineKind.QUESTION, LineKind.SUBQUESTION}
                        for line in lines
                    ):
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
                        sequence, current_parent_label = self._process_layout_page(
                            page,
                            layout_lines,
                            page_number,
                            sequence,
                            current_parent_label,
                            questions,
                            evidence,
                            structured.materials,
                        )
                else:
                    (
                        sequence,
                        current_parent_label,
                        detection,
                        average_confidence,
                        ocr_text_lines,
                    ) = self._process_ocr_page(
                        page,
                        page_number,
                        sequence,
                        current_parent_label,
                        questions,
                        evidence,
                    )
                    structured = extract_page_materials(
                        page,
                        ocr_text_lines,
                        page_number=page_number,
                        extraction_method="ocr",
                        detect_embedded_assets=False,
                    )
                    supporting_materials.extend(structured.materials)
                    supporting_annotations.extend(structured.annotations)
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
        methods_by_page = {item.page_number: item.extraction_method for item in diagnostics}
        document_references: list[ExtractedDocumentReference] = []
        for question in questions:
            document_references.extend(
                extract_question_references(
                    text=question.text,
                    question_number_label=question.number_label,
                    page_number=question.page_number,
                    geometry=question.geometry,
                    confidence=question.confidence,
                    extraction_method=methods_by_page.get(question.page_number, "direct_text"),
                )
            )
        return ExtractionResult(
            questions=questions,
            evidence=evidence,
            document_language=document_language,
            page_diagnostics=diagnostics,
            supporting_materials=supporting_materials,
            supporting_annotations=supporting_annotations,
            document_references=document_references,
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

    def _process_layout_page(
        self,
        page: Page,
        lines: list[PdfLayoutLine],
        page_number: int,
        sequence: int,
        current_parent_label: str | None,
        questions: list[ExtractedQuestion],
        evidence: list[ExtractedEvidence],
        materials: list[ExtractedSupportingMaterial],
    ) -> tuple[int, str | None]:
        draft: _QuestionDraft | None = None
        stopped = False

        def flush() -> None:
            nonlocal sequence, draft
            if draft is None:
                return
            number_label = draft.classified.number_label
            assert number_label is not None
            geometry = _union_geometry(draft.geometries)
            reading_text = _joined_stem(draft.reading_parts)
            raw_text = "\n".join(draft.raw_parts)
            marks = draft.classified.marks
            sequence += 1
            questions.append(
                ExtractedQuestion(
                    number_label=number_label,
                    text=reading_text,
                    page_number=draft.page_number,
                    parent_number_label=draft.parent_number_label,
                    marks=marks.value if marks else None,
                    sequence=sequence,
                    confidence=_confidence_for(geometry),
                    geometry=geometry,
                )
            )
            evidence.append(
                ExtractedEvidence(
                    evidence_type="question_text",
                    page_number=draft.page_number,
                    item_reference=number_label,
                    extracted_text=reading_text,
                    confidence=_confidence_for(geometry),
                    geometry=geometry,
                    question_number_label=number_label,
                )
            )
            if raw_text != reading_text:
                evidence.append(
                    ExtractedEvidence(
                        evidence_type="question_source_spans",
                        page_number=draft.page_number,
                        item_reference=number_label,
                        extracted_text=raw_text,
                        confidence=_confidence_for(geometry),
                        geometry=geometry,
                        question_number_label=number_label,
                    )
                )
            if marks is not None:
                evidence.append(
                    ExtractedEvidence(
                        evidence_type="marks",
                        page_number=draft.page_number,
                        item_reference=number_label,
                        extracted_text=marks.matched_text,
                        confidence=_confidence_for(draft.marks_geometry),
                        geometry=draft.marks_geometry,
                        question_number_label=number_label,
                    )
                )
            draft = None

        for line in lines:
            classified = classify_line(line.reading_text, current_parent_label)
            if classified.kind in {LineKind.QUESTION, LineKind.SUBQUESTION}:
                flush()
                parent_label = (
                    current_parent_label if classified.kind is LineKind.SUBQUESTION else None
                )
                if classified.kind is LineKind.QUESTION:
                    current_parent_label = classified.number_label
                draft = _QuestionDraft(
                    classified=classified,
                    page_number=page_number,
                    parent_number_label=parent_label,
                    reading_parts=[line.reading_text],
                    raw_parts=[line.raw_text],
                    geometries=[line.geometry],
                    marks_geometry=line.geometry if classified.marks is not None else None,
                )
                stopped = False
                continue

            if classified.kind in {LineKind.INSTRUCTIONS, LineKind.TOTAL_MARKS}:
                geometry = line.geometry
                evidence_type = (
                    "instructions" if classified.kind is LineKind.INSTRUCTIONS else "declared_total"
                )
                evidence.append(
                    ExtractedEvidence(
                        evidence_type=evidence_type,
                        page_number=page_number,
                        item_reference=(
                            "instructions" if evidence_type == "instructions" else "total"
                        ),
                        extracted_text=line.reading_text,
                        confidence=_confidence_for(geometry),
                        geometry=geometry,
                        question_number_label=None,
                    )
                )
                continue

            if draft is None or stopped:
                continue
            previous_bottom = draft.geometries[-1].bottom
            crosses_material = any(
                item.geometry is not None
                and previous_bottom < item.geometry.top < line.geometry.top
                for item in materials
            )
            inside_material = any(
                item.geometry is not None
                and item.geometry.top <= line.geometry.top
                and line.geometry.bottom <= item.geometry.bottom
                for item in materials
            )
            looks_like_footer = "Batch" in line.reading_text and "/" in line.reading_text
            if (
                line.geometry.top - previous_bottom > _STEM_VERTICAL_GAP
                or crosses_material
                or inside_material
                or looks_like_footer
            ):
                stopped = True
                continue
            draft.reading_parts.append(line.reading_text)
            draft.raw_parts.append(line.raw_text)
            draft.geometries.append(line.geometry)

        flush()
        return sequence, current_parent_label

    def _process_ocr_page(
        self,
        page: Page,
        page_number: int,
        sequence: int,
        current_parent_label: str | None,
        questions: list[ExtractedQuestion],
        evidence: list[ExtractedEvidence],
    ) -> tuple[int, str | None, LanguageDetection, float, list[str]]:
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
        return (
            sequence,
            current_parent_label,
            detection,
            round(average_confidence, 4),
            [line.text for line in ocr_lines],
        )

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
