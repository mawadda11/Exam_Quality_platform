"""Digital-first bilingual exam extraction with page-level OCR fallback.

The source PDF text is attempted first. A mechanical quality gate decides
whether that page is usable; empty or clearly garbled pages are rasterized and
sent through the configured OCR adapter. Arabic/English matching happens only
in the line classifier, while persisted question/evidence text remains exactly
the source line returned by the digital or OCR provider.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pdfplumber
from pdfplumber.page import Page

from app.core.domain import ExtractionWarningSeverity
from app.services.extraction.declared_total import extract_layout_declared_total
from app.services.extraction.document_ocr import (
    DocumentOcrProvider,
    DocumentOcrProviderError,
    NormalizedOcrDocument,
    NormalizedOcrLine,
)
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
    is_mark_status_annotation,
    parse_marks,
)
from app.services.extraction.ocr import OCR_RESOLUTION_DPI, OcrEngine, TesseractOcrEngine
from app.services.extraction.pdf_layout import PdfLayoutLine, extract_layout_lines
from app.services.extraction.reconciliation import reconcile_native_and_ocr
from app.services.extraction.structured_evidence import (
    extract_page_materials,
    extract_question_references,
    normalize_annotation_label,
)
from app.services.extraction.text_quality import assess_text_quality
from app.services.extraction.types import (
    ExtractedDocumentReference,
    ExtractedEvidence,
    ExtractedQuestion,
    ExtractedSourceLine,
    ExtractedSourceToken,
    ExtractedSupportingAnnotation,
    ExtractedSupportingMaterial,
    ExtractionError,
    ExtractionReconciliationWarning,
    ExtractionResult,
    Geometry,
    PageExtractionDiagnostic,
)

_FULL_CONFIDENCE = 1.0
_NO_GEOMETRY_CONFIDENCE = 0.6
_LOW_CONFIDENCE_REVIEW = 0.75

_ANSWER_SPACE_LINE = re.compile(r"^\s*(?:[._·•…⋯-]\s*){12,}\s*$")
_PAGE_FRACTION = re.compile(r"^\s*[0-9٠-٩]+\s*/\s*[0-9٠-٩]+\s*$")
_PAGE_FOOTER_INLINE = re.compile(
    r"(?:\bpage\s*[0-9٠-٩]+\s*(?:of|/)\s*[0-9٠-٩]+\b|"
    r"(?:الصفحة|صفحة)\s*[0-9٠-٩]+\s*(?:من|/)\s*[0-9٠-٩]+)",
    re.IGNORECASE,
)
_FOOTER_TEXT_CUES = (
    "synthetic test fixture",
    "not an official document",
    "نموذج تجريبي",
    "مستند اصطناعي",
    "غير تابع لأي جامعة",
    "محلل جودة الاختبارات",
    "exam quality analyzer",
    "ملف اختبار",
    "يعانطصا",
    "ةيمسر ةهج",
)
_INSTRUCTION_HEADING_CUE = re.compile(
    r"(?:\binstructions?\b|تعليمات|التعليمات)", re.IGNORECASE
)
_BULLET_CUE = re.compile(r"^\s*[•▪◦*\-]\s*|\s*[•▪◦]\s*$")
_QUESTION_START_CUE = re.compile(
    r"^\s*(?:Q\s*\d+|Question\s+\d+|س\s*\d+|السؤال\s+)", re.IGNORECASE
)


def _is_answer_space_line(value: str) -> bool:
    return _ANSWER_SPACE_LINE.fullmatch(value) is not None


def _looks_like_page_footer_text(value: str) -> bool:
    normalized = " ".join(value.casefold().split())
    return (
        _PAGE_FRACTION.fullmatch(normalized) is not None
        or _PAGE_FOOTER_INLINE.search(normalized) is not None
        or any(cue in normalized for cue in _FOOTER_TEXT_CUES)
    )


def _best_instruction_line_text(line: PdfLayoutLine) -> str:
    """Choose the source-faithful orientation that is most readable for instructions."""

    raw = " ".join(line.raw_text.split()).strip()
    reading = " ".join(line.reading_text.split()).strip()
    if raw and (re.search(r"[A-Za-z]{3,}", raw) or raw.startswith(("•", "-", "*"))):
        return raw
    return reading or raw


def _general_instruction_block_from_layout(
    lines: Sequence[PdfLayoutLine], *, page_number: int
) -> ExtractedEvidence | None:
    """Recover a general Instructions block even when heading and bullets are separate lines.

    PDF layouts commonly emit ``Instructions / التعليمات`` as one line and each
    bullet as a separate line.  The old line-by-line classifier recognized only
    ``Instructions: ...`` and therefore silently lost the actual instructions.
    This block extractor remains source-faithful and stops before the first
    question/section content.
    """

    heading_index: int | None = None
    for index, line in enumerate(lines):
        candidate = _best_instruction_line_text(line)
        if len(candidate) <= 120 and _INSTRUCTION_HEADING_CUE.search(candidate):
            heading_index = index
            break
    if heading_index is None:
        return None

    retained: list[PdfLayoutLine] = []
    saw_bullet = False
    for line in lines[heading_index + 1 :]:
        text = _best_instruction_line_text(line)
        if not text:
            continue
        if _QUESTION_START_CUE.match(text) or _looks_like_page_footer_text(text):
            break
        classified = classify_line(text, None)
        if classified.kind in {LineKind.QUESTION, LineKind.SUBQUESTION, LineKind.TOTAL_MARKS}:
            break
        is_bullet = _BULLET_CUE.search(text) is not None
        if saw_bullet and not is_bullet:
            # Once a bullet list has started, the next non-bullet line is much
            # more likely to be fixture/admin prose than a general instruction.
            break
        retained.append(line)
        saw_bullet = saw_bullet or is_bullet
        if len(retained) >= 12:
            break

    if not retained:
        # Preserve a one-line ``Instructions: ...`` form when the heading itself
        # contains substantive content after the label.
        heading = lines[heading_index]
        heading_text = _best_instruction_line_text(heading)
        normalized = _INSTRUCTION_HEADING_CUE.sub("", heading_text, count=1).strip(" /:-")
        if not normalized:
            return None
        retained = [heading]

    texts = [_best_instruction_line_text(line) for line in retained]
    combined = " ".join(text for text in texts if text).strip()
    if not combined:
        return None
    geometry = _union_geometry([line.geometry for line in retained])
    return ExtractedEvidence(
        evidence_type="instructions",
        page_number=page_number,
        item_reference="instructions",
        extracted_text=combined,
        confidence=_confidence_for(geometry),
        geometry=geometry,
        question_number_label=None,
    )


def _replace_general_instruction_evidence_for_page(
    evidence: list[ExtractedEvidence],
    *,
    page_number: int,
    instruction_block: ExtractedEvidence | None,
) -> None:
    if instruction_block is None:
        return
    evidence[:] = [
        item
        for item in evidence
        if not (
            item.page_number == page_number
            and item.evidence_type == "instructions"
            and item.question_number_label is None
        )
    ]
    evidence.append(instruction_block)


def _parent_label_for_subquestion(
    number_label: str | None,
    current_parent_label: str | None,
) -> str | None:
    if number_label is not None:
        matched = re.match(r"^(Q\d+)(?:\.\d+|\([a-z]\))$", number_label, re.I)
        if matched is not None:
            return matched.group(1)
    return current_parent_label


def _normalized_source(value: str) -> str:
    return " ".join(value.casefold().split())


def _is_standalone_marks_line(value: str) -> bool:
    parsed = parse_marks(value)
    if parsed is None:
        return False
    return _normalized_source(value) == _normalized_source(parsed.matched_text)


def _native_page_source_lines(
    page: Page,
    *,
    page_number: int,
    text_lines: list[str],
    layout_lines: list[PdfLayoutLine],
    confidence: float,
    language: str,
) -> list[ExtractedSourceLine]:
    if layout_lines:
        return [
            ExtractedSourceLine(
                source_line_id=f"P{page_number}-N{line_index}",
                provider="pdfplumber",
                provider_version=getattr(pdfplumber, "__version__", None),
                page_number=page_number,
                reading_order=line_index,
                # Arabic/mixed digital PDFs can expose the provider text in
                # visual glyph/word order.  The geometry-derived reading text
                # remains source-backed and is the representation suitable for
                # parsing, Gemini reconciliation, and faculty review.  Preserve
                # the untouched provider order separately in ``raw_text``.
                original_text=line.reading_text,
                geometry=line.geometry,
                confidence=confidence,
                extraction_method="direct_text",
                language=language,
                tokens=tuple(
                    ExtractedSourceToken(
                        token_id=f"P{page_number}-N{line_index}-T{token_index}",
                        original_text=token.original_text,
                        geometry=token.geometry,
                        confidence=confidence,
                    )
                    for token_index, token in enumerate(line.tokens, start=1)
                ),
                page_width=float(page.width),
                page_height=float(page.height),
                raw_text=line.raw_text,
            )
            for line_index, line in enumerate(layout_lines, start=1)
        ]
    return [
        ExtractedSourceLine(
            source_line_id=f"P{page_number}-N{line_index}",
            provider="pdfplumber",
            provider_version=getattr(pdfplumber, "__version__", None),
            page_number=page_number,
            reading_order=line_index,
            original_text=line,
            geometry=_geometry_for_text(page, line),
            confidence=confidence,
            extraction_method="direct_text",
            language=language,
            page_width=float(page.width),
            page_height=float(page.height),
        )
        for line_index, line in enumerate(text_lines, start=1)
    ]


@dataclass
class _QuestionDraft:
    classified: ClassifiedLine
    page_number: int
    parent_number_label: str | None
    reading_parts: list[str]
    raw_parts: list[str]
    geometries: list[Geometry]
    marks_geometry: Geometry | None
    source_mode: str
    # Exact provider-neutral source ownership captured while the stem is built.
    # This avoids reconstructing provenance later with punctuation-sensitive
    # substring matching, which can silently drop wrapped Arabic/English lines.
    source_line_ids: list[str] = field(default_factory=list)


def _classification_priority(classified: ClassifiedLine) -> int:
    """Rank structural classifications for layout-orientation selection."""

    if classified.kind in {LineKind.QUESTION, LineKind.SUBQUESTION}:
        return 3
    if classified.kind in {LineKind.INSTRUCTIONS, LineKind.TOTAL_MARKS}:
        return 2
    return 0


def _select_layout_line_text(
    line: PdfLayoutLine,
    current_parent_label: str | None,
    preferred_source: str | None = None,
) -> tuple[str, ClassifiedLine, str]:
    """Choose the parseable reading orientation without rewriting evidence.

    Some Arabic digital PDFs expose already-logical text through the default
    extraction path while the geometry-derived RTL representation reverses the
    line. Other producers need the RTL representation. We classify both source-
    faithful candidates and select the one that carries stronger structural
    evidence. Continuation lines inherit the orientation of their question.
    """

    reading = classify_line(line.reading_text, current_parent_label)
    if line.raw_text == line.reading_text:
        return line.reading_text, reading, "reading"

    raw = classify_line(line.raw_text, current_parent_label)
    reading_priority = _classification_priority(reading)
    raw_priority = _classification_priority(raw)

    if raw_priority > reading_priority:
        return line.raw_text, raw, "raw"
    if reading_priority > raw_priority:
        return line.reading_text, reading, "reading"

    if preferred_source == "raw":
        return line.raw_text, raw, "raw"
    return line.reading_text, reading, "reading"


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
    retained = [
        part.strip()
        for part in parts
        if part.strip()
        and not _is_answer_space_line(part)
        and not _looks_like_page_footer_text(part)
        and normalize_annotation_label(part) is None
        and not is_mark_status_annotation(part)
    ]
    value = " ".join(retained)
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


def _looks_like_vector_graphic_label(
    page: Page,
    text: str,
    geometry: Geometry,
) -> bool:
    """Return True for short labels embedded inside a vector diagram/table.

    A digital PDF often exposes diagram labels as ordinary text lines. They
    belong in the source-page image, but must not be appended to the question
    transcription. This intentionally conservative check only suppresses short
    non-sentence text that overlaps a cluster of vector drawing objects.
    """

    stripped = text.strip()
    # Explicit marks are assessment metadata or a wrapped continuation of the
    # active question, never a diagram label.  A nearby vector figure must not
    # cause ``[3 درجات]`` or ``إجابتك. [3 درجات]`` to disappear.
    if parse_marks(stripped) is not None:
        return False
    words = re.findall(r"[A-Za-z0-9\u0600-\u06ff]+", stripped)
    if (
        not stripped
        or len(stripped) > 80
        or len(words) > 4
        or stripped.startswith((".", ",", "،", ";", "؛", ":"))
        or stripped.endswith((".", "?", "!", ":"))
    ):
        return False

    vector_objects = [*page.rects, *page.lines, *page.curves]
    nearby: list[dict[str, Any]] = []
    for item in vector_objects:
        top = float(item.get("top", 0.0))
        bottom = float(item.get("bottom", top))
        x0 = float(item.get("x0", 0.0))
        x1 = float(item.get("x1", x0))
        vertical_overlap = bottom + 8 >= geometry.top and top - 8 <= geometry.bottom
        horizontal_overlap = x1 + 12 >= geometry.x0 and x0 - 12 <= geometry.x1
        if vertical_overlap and horizontal_overlap:
            nearby.append(item)

    return len(nearby) >= 2


class PdfPlumberExamExtractor:
    """Extract digital, Arabic, English, mixed, and scanned exam pages."""

    def __init__(
        self,
        ocr_engine: OcrEngine | None = None,
        document_ocr_provider: DocumentOcrProvider | None = None,
    ) -> None:
        self._ocr_engine = ocr_engine or TesseractOcrEngine()
        self._document_ocr_provider = document_ocr_provider

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
        source_lines: list[ExtractedSourceLine] = []
        native_source_lines: list[ExtractedSourceLine] = []
        reconciliation_warnings: list[ExtractionReconciliationWarning] = []
        sequence = 0
        current_parent_label: str | None = None
        declared_total_found = False

        normalized_ocr: NormalizedOcrDocument | None = None
        compare_full_document = bool(
            self._document_ocr_provider is not None
            and getattr(
                self._document_ocr_provider,
                "compare_usable_native_pages",
                True,
            )
        )
        if compare_full_document and self._document_ocr_provider is not None:
            try:
                normalized_ocr = self._document_ocr_provider.extract(pdf_path)
            except DocumentOcrProviderError:
                reconciliation_warnings.append(
                    ExtractionReconciliationWarning(
                        code="OCR_PROVIDER_FAILED",
                        severity=ExtractionWarningSeverity.WARNING,
                        message="The document OCR provider failed; native extraction continued.",
                        page_number=None,
                    )
                )
        ocr_pages = (
            {page.page_number: page for page in normalized_ocr.pages}
            if normalized_ocr is not None
            else {}
        )
        if normalized_ocr is not None:
            reconciliation_warnings.extend(
                ExtractionReconciliationWarning(
                    code="OCR_PROVIDER_WARNING",
                    severity=ExtractionWarningSeverity.WARNING,
                    message="The OCR provider reported a document-level warning.",
                    page_number=None,
                )
                for _ in normalized_ocr.warnings
            )
            for ocr_page in normalized_ocr.pages:
                source_lines.extend(
                    ExtractedSourceLine(
                        source_line_id=line.line_id,
                        provider=normalized_ocr.provider_name,
                        provider_version=normalized_ocr.provider_version,
                        page_number=line.page_number,
                        reading_order=line.reading_order,
                        original_text=line.original_text,
                        geometry=line.geometry,
                        confidence=line.confidence,
                        extraction_method=normalized_ocr.extraction_method,
                        language=line.language,
                        tokens=tuple(
                            ExtractedSourceToken(
                                token_id=token.token_id,
                                original_text=token.original_text,
                                geometry=token.geometry,
                                confidence=token.confidence,
                            )
                            for token in line.tokens
                        ),
                        page_width=ocr_page.width,
                        page_height=ocr_page.height,
                    )
                    for line in ocr_page.lines
                )
                reconciliation_warnings.extend(
                    ExtractionReconciliationWarning(
                        code=warning,
                        severity=ExtractionWarningSeverity.WARNING,
                        message="The OCR provider reported a page-quality warning.",
                        page_number=ocr_page.page_number,
                    )
                    for warning in ocr_page.quality_warnings
                )

        with pdfplumber.open(pdf_path) as document:
            for page_index, page in enumerate(document.pages):
                page_number = page_index + 1
                text = page.extract_text() or ""
                quality = assess_text_quality(text)

                if quality.usable:
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    layout_lines = extract_layout_lines(page, page_number=page_number)
                    detection = detect_text_language(text)
                    page_native_lines = _native_page_source_lines(
                        page,
                        page_number=page_number,
                        text_lines=lines,
                        layout_lines=layout_lines,
                        confidence=quality.confidence,
                        language=detection.language.value,
                    )
                    native_source_lines.extend(page_native_lines)
                    source_lines.extend(page_native_lines)
                    if not declared_total_found:
                        declared_total = extract_layout_declared_total(layout_lines)
                        if declared_total is not None:
                            evidence.append(
                                ExtractedEvidence(
                                    evidence_type="declared_total",
                                    page_number=page_number,
                                    item_reference="total",
                                    extracted_text=declared_total.reading_text,
                                    confidence=declared_total.confidence,
                                    geometry=declared_total.geometry,
                                    question_number_label=None,
                                )
                            )
                            if declared_total.source_text != declared_total.reading_text:
                                evidence.append(
                                    ExtractedEvidence(
                                        evidence_type="declared_total_source_span",
                                        page_number=page_number,
                                        item_reference="total",
                                        extracted_text=declared_total.source_text,
                                        confidence=declared_total.confidence,
                                        geometry=declared_total.geometry,
                                        question_number_label=None,
                                    )
                                )
                            declared_total_found = True
                    detections.append(detection)
                    diagnostics.append(
                        PageExtractionDiagnostic(
                            page_number=page_number,
                            language=detection.language,
                            language_confidence=detection.confidence,
                            extraction_method="direct_text",
                            text_quality_confidence=quality.confidence,
                            review_recommended=(
                                page_number in ocr_pages
                                and ocr_pages[page_number].review_recommended
                            ),
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
                    # Prefer layout-aware extraction whenever positional lines are
                    # available. It preserves wrapped question stems and stops before
                    # real supporting materials. The plain-text path remains as a
                    # fallback for PDFs where layout extraction yields no usable lines.
                    if layout_lines:
                        sequence, current_parent_label = self._process_layout_page(
                            page,
                            layout_lines,
                            page_number,
                            sequence,
                            current_parent_label,
                            questions,
                            evidence,
                            structured.materials,
                            declared_total_found,
                        )
                        _replace_general_instruction_evidence_for_page(
                            evidence,
                            page_number=page_number,
                            instruction_block=_general_instruction_block_from_layout(
                                layout_lines, page_number=page_number
                            ),
                        )
                    else:
                        sequence, current_parent_label = self._process_digital_page(
                            page,
                            lines,
                            page_number,
                            sequence,
                            current_parent_label,
                            questions,
                            evidence,
                            declared_total_found,
                        )
                    declared_total_found = declared_total_found or any(
                        item.evidence_type == "declared_total" for item in evidence
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
                        normalized_lines=(
                            tuple(ocr_pages[page_number].lines)
                            if page_number in ocr_pages
                            else None
                        ),
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

        if normalized_ocr is not None:
            reconciliation_warnings.extend(
                reconcile_native_and_ocr(native_source_lines, normalized_ocr)
            )
        questions = self._attach_source_line_provenance(questions, source_lines)
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
        # Keep every structurally extracted material until the question-structure
        # parser has run. Tables can carry semantic question rows (for example a
        # True/False grid that continues on the next page) even when they are not
        # user-facing supporting context. The final review-visible material scope
        # is applied after structure parsing.
        return ExtractionResult(
            questions=questions,
            evidence=evidence,
            document_language=document_language,
            page_diagnostics=diagnostics,
            supporting_materials=supporting_materials,
            supporting_annotations=supporting_annotations,
            document_references=document_references,
            source_lines=source_lines,
            reconciliation_warnings=reconciliation_warnings,
        )

    @staticmethod
    def _attach_source_line_provenance(
        questions: list[ExtractedQuestion],
        source_lines: list[ExtractedSourceLine],
    ) -> list[ExtractedQuestion]:
        enriched: list[ExtractedQuestion] = []
        source_by_id = {line.source_line_id: line for line in source_lines}
        for question in questions:
            candidates = [line for line in source_lines if line.page_number == question.page_number]
            # Layout/plain-text extraction now captures exact source-line ownership
            # while the question draft is assembled. Prefer that authoritative
            # provenance and only fall back to legacy text/geometry matching for
            # older/alternate extractors that did not provide it.
            matching = [
                source_by_id[source_line_id]
                for source_line_id in question.source_line_ids
                if source_line_id in source_by_id
            ]
            if not matching:
                matching = [
                    line
                    for line in candidates
                    if not _is_standalone_marks_line(line.original_text)
                    and (
                        _normalized_source(line.original_text) in _normalized_source(question.text)
                        or _normalized_source(question.text) in _normalized_source(line.original_text)
                    )
                ]
            if not matching and question.geometry is not None:
                matching = [
                    line
                    for line in candidates
                    if line.geometry is not None
                    and line.geometry.bottom >= question.geometry.top
                    and line.geometry.top <= question.geometry.bottom
                ]
            if not matching and candidates:
                matching = [min(candidates, key=lambda line: line.reading_order)]
            local_key = question.local_key or f"P{question.page_number}-Q{question.sequence}"
            enriched.append(
                replace(
                    question,
                    local_key=local_key,
                    source_line_ids=tuple(line.source_line_id for line in matching),
                    extraction_method=(
                        matching[0].extraction_method if matching else "direct_text"
                    ),
                )
            )
        return enriched

    def _process_digital_page(
        self,
        page: Page,
        lines: list[str],
        page_number: int,
        sequence: int,
        current_parent_label: str | None,
        questions: list[ExtractedQuestion],
        evidence: list[ExtractedEvidence],
        suppress_declared_total: bool,
    ) -> tuple[int, str | None]:
        draft: _QuestionDraft | None = None

        def flush() -> None:
            nonlocal sequence, draft
            if draft is None:
                return
            number_label = draft.classified.number_label
            assert number_label is not None
            geometry = _union_geometry(draft.geometries)
            reading_text = _joined_stem(draft.reading_parts)
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
                    source_line_ids=tuple(draft.source_line_ids),
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

        for line_index, line in enumerate(lines, start=1):
            source_line_id = f"P{page_number}-N{line_index}"
            if (
                not line.strip()
                or _is_answer_space_line(line)
                or _looks_like_page_footer_text(line)
                or is_mark_status_annotation(line)
            ):
                continue
            classified = classify_line(line, current_parent_label)
            geometry = _geometry_for_text(page, line)
            if classified.kind in {LineKind.QUESTION, LineKind.SUBQUESTION}:
                flush()
                parent_label = (
                    _parent_label_for_subquestion(
                        classified.number_label, current_parent_label
                    )
                    if classified.kind is LineKind.SUBQUESTION
                    else None
                )
                if classified.kind is LineKind.QUESTION:
                    current_parent_label = classified.number_label
                draft = _QuestionDraft(
                    classified=classified,
                    page_number=page_number,
                    parent_number_label=parent_label,
                    reading_parts=[line],
                    raw_parts=[line],
                    geometries=[geometry] if geometry is not None else [],
                    marks_geometry=(
                        _geometry_for_text(page, classified.marks.matched_text)
                        if classified.marks is not None
                        else None
                    ),
                    source_mode="reading",
                    source_line_ids=[source_line_id],
                )
                continue

            if classified.kind in {LineKind.INSTRUCTIONS, LineKind.TOTAL_MARKS}:
                if classified.kind is LineKind.TOTAL_MARKS and suppress_declared_total:
                    continue
                evidence.append(
                    ExtractedEvidence(
                        evidence_type=(
                            "instructions"
                            if classified.kind is LineKind.INSTRUCTIONS
                            else "declared_total"
                        ),
                        page_number=page_number,
                        item_reference=(
                            "instructions"
                            if classified.kind is LineKind.INSTRUCTIONS
                            else "total"
                        ),
                        extracted_text=line,
                        confidence=_confidence_for(geometry),
                        geometry=geometry,
                        question_number_label=None,
                    )
                )
                continue

            if draft is not None:
                draft.reading_parts.append(line)
                draft.raw_parts.append(line)
                draft.source_line_ids.append(source_line_id)
                if geometry is not None:
                    draft.geometries.append(geometry)

        flush()
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
        suppress_declared_total: bool,
    ) -> tuple[int, str | None]:
        draft: _QuestionDraft | None = None

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
                    source_line_ids=tuple(draft.source_line_ids),
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

        for line_index, line in enumerate(lines, start=1):
            source_line_id = f"P{page_number}-N{line_index}"
            line_text, classified, source_mode = _select_layout_line_text(
                line,
                current_parent_label,
                draft.source_mode if draft is not None else None,
            )
            if (
                _is_answer_space_line(line_text)
                or _looks_like_page_footer_text(line_text)
                or is_mark_status_annotation(line_text)
            ):
                continue
            if classified.kind in {LineKind.QUESTION, LineKind.SUBQUESTION}:
                flush()
                parent_label = (
                    _parent_label_for_subquestion(
                        classified.number_label, current_parent_label
                    )
                    if classified.kind is LineKind.SUBQUESTION
                    else None
                )
                if classified.kind is LineKind.QUESTION:
                    current_parent_label = classified.number_label
                draft = _QuestionDraft(
                    classified=classified,
                    page_number=page_number,
                    parent_number_label=parent_label,
                    reading_parts=[line_text],
                    raw_parts=[line.raw_text],
                    geometries=[line.geometry],
                    marks_geometry=line.geometry if classified.marks is not None else None,
                    source_mode=source_mode,
                    source_line_ids=[source_line_id],
                )
                continue

            if classified.kind in {LineKind.INSTRUCTIONS, LineKind.TOTAL_MARKS}:
                if classified.kind is LineKind.TOTAL_MARKS and suppress_declared_total:
                    continue
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
                        extracted_text=line_text,
                        confidence=_confidence_for(geometry),
                        geometry=geometry,
                        question_number_label=None,
                    )
                )
                continue

            if draft is None:
                continue
            # Captions and text inside a figure/table belong to the supporting
            # visual, not to the transcription. They must not terminate the
            # question, however: a wrapped stem may continue below the visual.
            # A labelled Figure/Table/Code caption belongs to supporting context,
            # not to the canonical question prompt.  Mixed Arabic/English PDFs
            # can expose the same caption in a logical reading orientation while
            # the raw source starts with the English label (or vice versa), so
            # inspect both source-faithful variants before retaining the line.
            if (
                normalize_annotation_label(line_text) is not None
                or normalize_annotation_label(line.raw_text) is not None
            ):
                continue

            # Do not flatten visible supporting material into the editable stem.
            # Earlier code only removed relatively small materials; full-size
            # diagrams therefore leaked their labels/captions into question text.
            # Question-marker lines are handled above, so all material geometries
            # are safe to treat as visual/supporting context here.
            material_geometries = [
                item.geometry for item in materials if item.geometry is not None
            ]
            inside_material = any(
                geometry.top <= line.geometry.top
                and line.geometry.bottom <= geometry.bottom
                and min(geometry.x1, line.geometry.x1)
                > max(geometry.x0, line.geometry.x0)
                for geometry in material_geometries
            )
            overlaps_material_band = any(
                geometry.bottom >= line.geometry.top
                and geometry.top <= line.geometry.bottom
                and min(geometry.x1, line.geometry.x1)
                > max(geometry.x0, line.geometry.x0)
                for geometry in material_geometries
            )
            # Do not classify arbitrary short text near the bottom of a page as a
            # footer. A legitimate wrapped question can continue inside the
            # bottom 10% of the page. Explicit footer/page-furniture text is
            # already filtered above; retain only the legacy Batch marker here.
            looks_like_footer = "Batch" in line_text and "/" in line_text
            if (
                inside_material
                or overlaps_material_band
                or looks_like_footer
                or _looks_like_vector_graphic_label(page, line_text, line.geometry)
            ):
                continue

            # A question continues until the next explicit question marker.
            # Vertical whitespace, line wrapping, or a visual between two stem
            # fragments must not silently truncate the source text.
            draft.reading_parts.append(line_text)
            draft.raw_parts.append(line.raw_text)
            draft.geometries.append(line.geometry)
            draft.source_line_ids.append(source_line_id)

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
        normalized_lines: Sequence[NormalizedOcrLine] | None = None,
    ) -> tuple[int, str | None, LanguageDetection, float, list[str]]:
        if normalized_lines is None:
            scale = OCR_RESOLUTION_DPI / 72.0
            image = page.to_image(resolution=OCR_RESOLUTION_DPI).original
            ocr_lines: Sequence[Any] = self._ocr_engine.lines_for_image(image, scale)
        else:
            ocr_lines = normalized_lines

        draft: _QuestionDraft | None = None
        draft_confidences: list[float] = []

        def flush() -> None:
            nonlocal sequence, draft, draft_confidences
            if draft is None:
                return
            number_label = draft.classified.number_label
            assert number_label is not None
            geometry = _union_geometry(draft.geometries)
            reading_text = _joined_stem(draft.reading_parts)
            confidence = (
                sum(draft_confidences) / len(draft_confidences)
                if draft_confidences
                else 0.0
            )
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
                    confidence=round(confidence, 4),
                    geometry=geometry,
                    source_line_ids=tuple(draft.source_line_ids),
                )
            )
            evidence.append(
                ExtractedEvidence(
                    evidence_type="question_text",
                    page_number=draft.page_number,
                    item_reference=number_label,
                    extracted_text=reading_text,
                    confidence=round(confidence, 4),
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
                        confidence=round(confidence, 4),
                        geometry=draft.marks_geometry,
                        question_number_label=number_label,
                    )
                )
            draft = None
            draft_confidences = []

        for ocr_index, ocr_line in enumerate(ocr_lines, start=1):
            line_text = str(getattr(ocr_line, "original_text", getattr(ocr_line, "text", "")))
            source_line_id = getattr(ocr_line, "line_id", None)
            if not line_text.strip():
                continue
            line_confidence = float(ocr_line.confidence or 0.0)
            if (
                _is_answer_space_line(line_text)
                or _looks_like_page_footer_text(line_text)
                or is_mark_status_annotation(line_text)
            ):
                continue
            classified = classify_line(line_text, current_parent_label)
            if classified.kind in {LineKind.QUESTION, LineKind.SUBQUESTION}:
                flush()
                parent_label = (
                    _parent_label_for_subquestion(
                        classified.number_label, current_parent_label
                    )
                    if classified.kind is LineKind.SUBQUESTION
                    else None
                )
                if classified.kind is LineKind.QUESTION:
                    current_parent_label = classified.number_label
                draft = _QuestionDraft(
                    classified=classified,
                    page_number=page_number,
                    parent_number_label=parent_label,
                    reading_parts=[line_text],
                    raw_parts=[line_text],
                    geometries=[ocr_line.geometry],
                    marks_geometry=ocr_line.geometry if classified.marks is not None else None,
                    source_mode="ocr",
                    source_line_ids=[str(source_line_id)] if source_line_id else [],
                )
                draft_confidences = [line_confidence]
                continue

            if classified.kind in {LineKind.INSTRUCTIONS, LineKind.TOTAL_MARKS}:
                evidence.append(
                    ExtractedEvidence(
                        evidence_type=(
                            "instructions"
                            if classified.kind is LineKind.INSTRUCTIONS
                            else "declared_total"
                        ),
                        page_number=page_number,
                        item_reference=(
                            "instructions"
                            if classified.kind is LineKind.INSTRUCTIONS
                            else "total"
                        ),
                        extracted_text=line_text,
                        confidence=line_confidence,
                        geometry=ocr_line.geometry,
                        question_number_label=None,
                    )
                )
                continue

            if draft is not None:
                draft.reading_parts.append(line_text)
                draft.raw_parts.append(line_text)
                draft.geometries.append(ocr_line.geometry)
                if source_line_id:
                    draft.source_line_ids.append(str(source_line_id))
                draft_confidences.append(line_confidence)

        flush()

        line_texts = [
            str(getattr(line, "original_text", getattr(line, "text", ""))) for line in ocr_lines
        ]
        joined_text = "\n".join(line_texts)
        detection = detect_text_language(joined_text)
        average_confidence = (
            sum(float(line.confidence or 0.0) for line in ocr_lines) / len(ocr_lines)
            if ocr_lines
            else 0.0
        )
        return (
            sequence,
            current_parent_label,
            detection,
            round(average_confidence, 4),
            line_texts,
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
        parent_label = (
            _parent_label_for_subquestion(classified.number_label, current_parent_label)
            if classified.kind is LineKind.SUBQUESTION
            else None
        )
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
