"""Adaptive, source-faithful Course Specification extractor.

The historical class name ``PdfPlumberTp153Extractor`` remains as a
compatibility alias because Version 1 routes/tests import it. Version 2 treats
TP-153 as one supported Course Specification layout rather than the only
layout. The parser supports section-heading, compact, table-led, reordered,
Arabic, English, and mixed variants without inventing absent records.
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
from app.services.extraction.ocr import OCR_RESOLUTION_DPI, OcrEngine, TesseractOcrEngine
from app.services.extraction.text_normalization import (
    normalize_arabic_for_matching,
    parse_localized_number,
    to_ascii_digits,
)
from app.services.extraction.text_quality import assess_text_quality
from app.services.extraction.types import (
    ExtractedAssessmentRecord,
    ExtractedClo,
    ExtractedCourseField,
    ExtractedTopic,
    ExtractionError,
    Geometry,
    PageExtractionDiagnostic,
    Tp153ExtractionResult,
    Tp153MissingEvidence,
)

_DIGITS = r"[0-9٠-٩۰-۹]+"
_NUMBER = rf"{_DIGITS}(?:[\.,][0-9٠-٩۰-۹]+)?"
_PERCENT = rf"(?P<percentage>{_NUMBER})\s*[٪%]"
_HOURS = rf"(?P<hours>{_NUMBER})\s*(?:hours?|hrs?|ساعات?|ساعة)"

_CLO_EXPLICIT = re.compile(
    rf"^(?:CLO|مخرج(?:ات)?(?:\s+التعلم)?|ناتج(?:ات)?(?:\s+التعلم)?)\s*"
    rf"(?P<number>{_DIGITS})\s*[:\-–—]?\s*(?P<text>.+?)"
    rf"(?:\s*[\[(](?P<po>(?:PLO\s*{_DIGITS}|مخرج\s+البرنامج\s*{_DIGITS}))[\])])?\s*$",
    re.IGNORECASE,
)
_CLO_CODE = re.compile(rf"^CLO\s*(?P<number>{_DIGITS})$", re.IGNORECASE)
_PO_CODE = re.compile(rf"^(?:PLO\s*{_DIGITS}|مخرج\s+البرنامج\s*{_DIGITS})$", re.IGNORECASE)

_TOPIC_EXPLICIT = re.compile(
    rf"^(?:(?:T|Topic)\s*(?P<number>{_DIGITS})|(?:الموضوع|موضوع)\s*(?P<arabic_number>{_DIGITS}))"
    rf"\s*[:\-–—]?\s*(?P<text>.+?)(?:\s*[-–—|]\s*{_HOURS})?\s*$",
    re.IGNORECASE,
)
_TOPIC_CODE = re.compile(rf"^(?:T|Topic)?\s*(?P<number>{_DIGITS})$", re.IGNORECASE)
_HOURS_ONLY = re.compile(rf"^{_HOURS}$", re.IGNORECASE)

_ASSESSMENT_FULL = re.compile(
    rf"^(?:Method|الطريقة|أسلوب\s+التقييم)\s*:\s*(?P<method>.+?)\s*\|\s*"
    rf"(?:Activity|النشاط)\s*:\s*(?P<activity>.+?)\s*\|\s*"
    rf"(?:Percentage|النسبة)\s*:\s*{_PERCENT}\s*$",
    re.IGNORECASE,
)
_ASSESSMENT_PARTIAL = re.compile(
    r"^(?:Method|الطريقة|أسلوب\s+التقييم)\s*:\s*(?P<method>.+?)\s*\|\s*"
    r"(?:Activity|النشاط)\s*:\s*(?P<activity>.+?)\s*$",
    re.IGNORECASE,
)
_COMPACT_ASSESSMENT = re.compile(
    r"^(?:Assessment|Assessments|التقييم|التقويم)\s*:?\s+(?P<items>.+)$",
    re.IGNORECASE,
)
_ASSESSMENT_ITEM = re.compile(rf"^(?P<method>.+?)\s+{_PERCENT}\s*$", re.IGNORECASE)
_PERCENT_ONLY = re.compile(rf"^{_PERCENT}$", re.IGNORECASE)

_METADATA_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "course_code",
        re.compile(r"^(?:Course\s+Code|رمز\s+المقرر)\s*[:\-]?\s*(?P<value>.+)$", re.I),
    ),
    (
        "course_name",
        re.compile(r"^(?:Course\s+Name|اسم\s+المقرر)\s*[:\-]?\s*(?P<value>.+)$", re.I),
    ),
    (
        "department",
        re.compile(r"^(?:Department|القسم)\s*[:\-]?\s*(?P<value>.+)$", re.I),
    ),
    (
        "program",
        re.compile(r"^(?:Program|البرنامج)\s*[:\-]?\s*(?P<value>.+)$", re.I),
    ),
    (
        "contact_hours",
        re.compile(
            rf"^(?:Contact\s+Hours|Credit\s+Hours|الساعات\s+التدريسية|الساعات\s+المعتمدة)"
            rf"\s*[:\-]?\s*(?P<value>{_NUMBER})\s*$",
            re.I,
        ),
    ),
)

_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "clos": (
        "course learning outcomes",
        "learning outcomes",
        "clo(s)",
        "مخرجات تعلم المقرر",
        "مخرجات التعلم",
        "نواتج التعلم",
    ),
    "topics": (
        "course topics",
        "course content",
        "topics",
        "محتوى المقرر",
        "موضوعات المقرر",
        "الموضوعات",
    ),
    "assessment_records": (
        "assessment methods",
        "assessment activities",
        "methods of assessment",
        "طرق التقييم",
        "أساليب التقييم",
        "استراتيجيات التقويم",
        "التقييم",
    ),
}
_SECTION_LABELS: dict[str, str] = {
    "clos": "Course Learning Outcomes / مخرجات التعلم",
    "topics": "Course Topics / موضوعات المقرر",
    "assessment_records": "Assessment Methods / طرق التقييم",
}

_FULL_CONFIDENCE = 1.0
_NO_GEOMETRY_CONFIDENCE = 0.6
_LOW_CONFIDENCE_REVIEW = 0.75
_CELL_SPLIT = re.compile(r"\s*\|\s*|\t+|\s{2,}")


@dataclass(frozen=True)
class CourseSpecificationLine:
    text: str
    page_number: int
    confidence: float = 1.0
    geometry: Geometry | None = None


def _geometry_from_match(match: dict[str, Any]) -> Geometry:
    return Geometry(
        x0=float(match["x0"]),
        top=float(match["top"]),
        x1=float(match["x1"]),
        bottom=float(match["bottom"]),
    )


def _geometry_for_text(page: Page, text: str) -> Geometry | None:
    try:
        matches = page.search(re.escape(text))
    except Exception:
        return None
    return _geometry_from_match(matches[0]) if matches else None


def _direct_confidence(geometry: Geometry | None) -> float:
    return _FULL_CONFIDENCE if geometry is not None else _NO_GEOMETRY_CONFIDENCE


def _canonical_code(prefix: str, token: str) -> str:
    return f"{prefix}{int(to_ascii_digits(token))}"


def _canonical_po(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.search(_DIGITS, value)
    return f"PLO{int(to_ascii_digits(digits.group()))}" if digits is not None else value.strip()


def _cells(text: str) -> list[str]:
    if "|" not in text and "\t" not in text and re.search(r"\s{2,}", text) is None:
        return []
    return [cell.strip() for cell in _CELL_SPLIT.split(text) if cell.strip()]


def _section_for_header(text: str) -> str | None:
    normalized = normalize_arabic_for_matching(text).casefold().strip(" :-–—")
    for section, aliases in _SECTION_ALIASES.items():
        if any(normalized == alias.casefold() for alias in aliases):
            return section
    return None


def _scaled_confidence(line: CourseSpecificationLine, parser_confidence: float) -> float:
    return round(max(0.0, min(1.0, line.confidence * parser_confidence)), 4)


class AdaptiveCourseSpecificationExtractor:
    """Parse Course Specifications from digital and OCR source lines."""

    def __init__(self, ocr_engine: OcrEngine | None = None) -> None:
        self._ocr_engine = ocr_engine or TesseractOcrEngine()

    def extract(self, pdf_path: Path) -> Tp153ExtractionResult:
        try:
            lines, diagnostics = self._extract_source_lines(pdf_path)
            return self.parse_lines(lines, diagnostics=diagnostics)
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError(
                f"Failed to parse Course Specification PDF: {pdf_path.name}"
            ) from exc

    def _extract_source_lines(
        self, pdf_path: Path
    ) -> tuple[list[CourseSpecificationLine], list[PageExtractionDiagnostic]]:
        source_lines: list[CourseSpecificationLine] = []
        diagnostics: list[PageExtractionDiagnostic] = []

        with pdfplumber.open(pdf_path) as document:
            for page_index, page in enumerate(document.pages):
                page_number = page_index + 1
                text = page.extract_text() or ""
                quality = assess_text_quality(text)
                if quality.usable:
                    page_lines = [line.strip() for line in text.splitlines() if line.strip()]
                    for line in page_lines:
                        geometry = _geometry_for_text(page, line)
                        source_lines.append(
                            CourseSpecificationLine(
                                text=line,
                                page_number=page_number,
                                confidence=_direct_confidence(geometry),
                                geometry=geometry,
                            )
                        )
                    detection = detect_text_language(text)
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
                    continue

                scale = OCR_RESOLUTION_DPI / 72.0
                image = page.to_image(resolution=OCR_RESOLUTION_DPI).original
                ocr_lines = self._ocr_engine.lines_for_image(image, scale)
                for ocr_line in ocr_lines:
                    source_lines.append(
                        CourseSpecificationLine(
                            text=ocr_line.text,
                            page_number=page_number,
                            confidence=ocr_line.confidence,
                            geometry=ocr_line.geometry,
                        )
                    )
                joined = "\n".join(line.text for line in ocr_lines)
                detection = detect_text_language(joined)
                average_confidence = (
                    sum(line.confidence for line in ocr_lines) / len(ocr_lines)
                    if ocr_lines
                    else 0.0
                )
                diagnostics.append(
                    PageExtractionDiagnostic(
                        page_number=page_number,
                        language=detection.language,
                        language_confidence=detection.confidence,
                        extraction_method="ocr",
                        text_quality_confidence=round(average_confidence, 4),
                        review_recommended=average_confidence < _LOW_CONFIDENCE_REVIEW,
                        reason=quality.reason,
                    )
                )

        return source_lines, diagnostics

    def parse_lines(
        self,
        lines: list[CourseSpecificationLine],
        *,
        diagnostics: list[PageExtractionDiagnostic] | None = None,
    ) -> Tp153ExtractionResult:
        clos: list[ExtractedClo] = []
        topics: list[ExtractedTopic] = []
        assessment_records: list[ExtractedAssessmentRecord] = []
        course_fields: list[ExtractedCourseField] = []
        detections: list[LanguageDetection] = []
        current_section: str | None = None
        header_seen = False
        table_seen = False
        compact_seen = False
        last_page_number = max((line.page_number for line in lines), default=1)

        for line in lines:
            source = line.text.strip()
            if not source:
                continue
            detections.append(detect_text_language(source))

            section = _section_for_header(source)
            if section is not None:
                current_section = section
                header_seen = True
                continue

            metadata = self._parse_metadata(line)
            if metadata is not None:
                course_fields.append(metadata)
                continue

            cells = _cells(source)
            if (
                cells
                and _ASSESSMENT_FULL.match(source) is None
                and _ASSESSMENT_PARTIAL.match(source) is None
            ):
                table_seen = True

            clo = self._parse_clo(line, cells, current_section)
            if clo is not None:
                clos.append(clo)
                compact_seen = compact_seen or current_section != "clos"
                continue

            topic = self._parse_topic(line, cells, current_section)
            if topic is not None:
                topics.append(topic)
                compact_seen = compact_seen or current_section != "topics"
                continue

            records = self._parse_assessments(line, cells, current_section)
            if records:
                assessment_records.extend(records)
                compact_seen = compact_seen or current_section != "assessment_records"

        clos = self._dedupe_clos(clos)
        topics = self._dedupe_topics(topics)
        assessment_records = self._dedupe_assessments(assessment_records)
        course_fields = self._dedupe_course_fields(course_fields)

        section_records: dict[str, list[Any]] = {
            "clos": list(clos),
            "topics": list(topics),
            "assessment_records": list(assessment_records),
        }
        missing_sections = [
            Tp153MissingEvidence(
                section=section,
                page_number=last_page_number,
                note=f"No source records were found for {label} in the Course Specification.",
            )
            for section, label in _SECTION_LABELS.items()
            if not section_records[section]
        ]

        if table_seen:
            layout_family = "table_led"
        elif header_seen:
            layout_family = "section_heading"
        elif compact_seen:
            layout_family = "compact"
        else:
            layout_family = "unknown"

        document_language = combine_page_languages(detections).language
        return Tp153ExtractionResult(
            clos=clos,
            topics=topics,
            assessment_records=assessment_records,
            missing_sections=missing_sections,
            course_fields=course_fields,
            layout_family=layout_family,
            document_language=document_language,
            page_diagnostics=list(diagnostics or []),
        )

    def _parse_metadata(self, line: CourseSpecificationLine) -> ExtractedCourseField | None:
        source = line.text.strip()
        for field_name, pattern in _METADATA_PATTERNS:
            match = pattern.match(source)
            if match is None:
                continue
            value = match.group("value").strip()
            return ExtractedCourseField(
                field_name=field_name,
                value=value,
                page_number=line.page_number,
                confidence=_scaled_confidence(line, 1.0),
                geometry=line.geometry,
            )
        return None

    def _parse_clo(
        self,
        line: CourseSpecificationLine,
        cells: list[str],
        current_section: str | None,
    ) -> ExtractedClo | None:
        code_match = _CLO_CODE.match(cells[0]) if cells else None
        if code_match is None and cells and current_section == "clos" and cells[0].isdigit():
            code_match = re.match(rf"^(?P<number>{_DIGITS})$", cells[0])
        if code_match is not None and len(cells) >= 2:
            po = next((cell for cell in cells[2:] if _PO_CODE.match(cell)), None)
            return ExtractedClo(
                code=_canonical_code("CLO", code_match.group("number")),
                text=cells[1],
                program_outcome_reference=_canonical_po(po),
                page_number=line.page_number,
                confidence=_scaled_confidence(line, 0.9),
                geometry=line.geometry,
            )

        explicit = _CLO_EXPLICIT.match(line.text.strip())
        if explicit is not None:
            return ExtractedClo(
                code=_canonical_code("CLO", explicit.group("number")),
                text=explicit.group("text").strip(),
                program_outcome_reference=_canonical_po(explicit.group("po")),
                page_number=line.page_number,
                confidence=_scaled_confidence(line, 1.0),
                geometry=line.geometry,
            )

        return None

    def _parse_topic(
        self,
        line: CourseSpecificationLine,
        cells: list[str],
        current_section: str | None,
    ) -> ExtractedTopic | None:
        explicit = _TOPIC_EXPLICIT.match(line.text.strip())
        if explicit is not None:
            number = explicit.group("number") or explicit.group("arabic_number")
            hours = explicit.group("hours")
            text = explicit.group("text").strip()
            if hours is not None:
                # The non-greedy text may still include the separator when a
                # PDF text layer uses unusual spaces; remove only a trailing one.
                text = text.rstrip(" -–—|")
            return ExtractedTopic(
                code=_canonical_code("T", number),
                text=text,
                expected_hours=parse_localized_number(hours) if hours else None,
                page_number=line.page_number,
                confidence=_scaled_confidence(line, 1.0),
                geometry=line.geometry,
            )

        if current_section != "topics" or len(cells) < 2:
            return None
        code_match = _TOPIC_CODE.match(cells[0])
        if code_match is None:
            return None
        hours_match = next(
            (match for cell in cells[2:] if (match := _HOURS_ONLY.match(cell)) is not None),
            None,
        )
        hours = hours_match.group("hours") if hours_match is not None else None
        return ExtractedTopic(
            code=_canonical_code("T", code_match.group("number")),
            text=cells[1],
            expected_hours=parse_localized_number(hours) if hours else None,
            page_number=line.page_number,
            confidence=_scaled_confidence(line, 0.85),
            geometry=line.geometry,
        )

    def _parse_assessments(
        self,
        line: CourseSpecificationLine,
        cells: list[str],
        current_section: str | None,
    ) -> list[ExtractedAssessmentRecord]:
        source = line.text.strip()
        full = _ASSESSMENT_FULL.match(source)
        if full is not None:
            return [
                ExtractedAssessmentRecord(
                    method=full.group("method").strip(),
                    activity=full.group("activity").strip(),
                    percentage=parse_localized_number(full.group("percentage")),
                    page_number=line.page_number,
                    confidence=_scaled_confidence(line, 1.0),
                    geometry=line.geometry,
                )
            ]

        partial = _ASSESSMENT_PARTIAL.match(source)
        if partial is not None:
            return [
                ExtractedAssessmentRecord(
                    method=partial.group("method").strip(),
                    activity=partial.group("activity").strip(),
                    percentage=None,
                    page_number=line.page_number,
                    confidence=_scaled_confidence(line, 1.0),
                    geometry=line.geometry,
                )
            ]

        compact = _COMPACT_ASSESSMENT.match(source)
        if compact is not None:
            records: list[ExtractedAssessmentRecord] = []
            items = re.split(r"\s*[,،]\s*", compact.group("items"))
            for item in items:
                item_match = _ASSESSMENT_ITEM.match(normalize_arabic_for_matching(item))
                if item_match is None:
                    continue
                records.append(
                    ExtractedAssessmentRecord(
                        method=item_match.group("method").strip(),
                        activity=None,
                        percentage=parse_localized_number(item_match.group("percentage")),
                        page_number=line.page_number,
                        confidence=_scaled_confidence(line, 0.9),
                        geometry=line.geometry,
                    )
                )
            return records

        if current_section != "assessment_records" or len(cells) < 2:
            return []
        percentage_index = next(
            (index for index, cell in enumerate(cells) if _PERCENT_ONLY.match(cell)), None
        )
        if percentage_index is None:
            # A table row can still be reviewable when it explicitly has a
            # method and activity but no percentage. Do not invent one.
            return [
                ExtractedAssessmentRecord(
                    method=cells[0],
                    activity=cells[1] if len(cells) > 1 else None,
                    percentage=None,
                    page_number=line.page_number,
                    confidence=_scaled_confidence(line, 0.75),
                    geometry=line.geometry,
                )
            ]
        percentage_match = _PERCENT_ONLY.match(cells[percentage_index])
        assert percentage_match is not None
        activity = cells[1] if percentage_index > 1 else None
        return [
            ExtractedAssessmentRecord(
                method=cells[0],
                activity=activity,
                percentage=parse_localized_number(percentage_match.group("percentage")),
                page_number=line.page_number,
                confidence=_scaled_confidence(line, 0.85),
                geometry=line.geometry,
            )
        ]

    @staticmethod
    def _dedupe_clos(records: list[ExtractedClo]) -> list[ExtractedClo]:
        by_code: dict[str, ExtractedClo] = {}
        for record in records:
            current = by_code.get(record.code)
            if current is None or record.confidence > current.confidence:
                by_code[record.code] = record
        return list(by_code.values())

    @staticmethod
    def _dedupe_topics(records: list[ExtractedTopic]) -> list[ExtractedTopic]:
        by_key: dict[str, ExtractedTopic] = {}
        for record in records:
            key = record.code or normalize_arabic_for_matching(record.text).casefold()
            current = by_key.get(key)
            if current is None or record.confidence > current.confidence:
                by_key[key] = record
        return list(by_key.values())

    @staticmethod
    def _dedupe_assessments(
        records: list[ExtractedAssessmentRecord],
    ) -> list[ExtractedAssessmentRecord]:
        by_key: dict[str, ExtractedAssessmentRecord] = {}
        for record in records:
            key = normalize_arabic_for_matching(record.method).casefold()
            current = by_key.get(key)
            if current is None or record.confidence > current.confidence:
                by_key[key] = record
        return list(by_key.values())

    @staticmethod
    def _dedupe_course_fields(records: list[ExtractedCourseField]) -> list[ExtractedCourseField]:
        by_name: dict[str, ExtractedCourseField] = {}
        for record in records:
            current = by_name.get(record.field_name)
            if current is None or record.confidence > current.confidence:
                by_name[record.field_name] = record
        return list(by_name.values())


class PdfPlumberTp153Extractor(AdaptiveCourseSpecificationExtractor):
    """Backward-compatible import name for Version 1 pipeline/tests."""
