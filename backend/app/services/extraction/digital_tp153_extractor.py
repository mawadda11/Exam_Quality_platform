"""Adaptive, source-faithful Course Specification extractor.

The historical class name ``PdfPlumberTp153Extractor`` remains as a
compatibility alias because Version 1 routes/tests import it. Version 2 treats
TP-153 as one supported Course Specification layout rather than the only
layout. The parser supports section-heading, compact, table-led, reordered,
Arabic, English, and mixed variants without inventing absent records.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
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
from app.services.extraction.pdf_layout import extract_layout_lines
from app.services.extraction.text_normalization import (
    normalize_arabic_for_matching,
    parse_localized_number,
    to_ascii_digits,
)
from app.services.extraction.text_quality import assess_text_quality
from app.services.extraction.types import (
    CourseSpecificationWarning,
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
_TOPIC_INLINE_CODE = re.compile(
    rf"(?<![A-Za-z0-9])(?:T|Topic)\s*(?P<number>{_DIGITS})(?![A-Za-z0-9-])",
    re.IGNORECASE,
)
_CLO_INLINE_CODE = re.compile(
    rf"(?<![A-Za-z0-9])CLO\s*(?P<number>{_DIGITS})(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_PAGE_FOOTER = re.compile(r"\bpage\s+\d+\s+of\s+\d+\b", re.IGNORECASE)
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
_ASSESSMENT_CLO_CODE = re.compile(r"\bCLO\s*([0-9٠-٩۰-۹]+)\b", re.IGNORECASE)

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
        "clos",
        "مخرجات تعلم المقرر",
        "مخرجات التعلم",
        "نواتج تعلم المقرر",
        "نواتج التعلم للمقرر",
        "نواتج التعلم",
    ),
    "topics": (
        "course topics",
        "course content",
        "topics",
        "محتوى المقرر",
        "موضوعات المقرر",
        "مواضيع المقرر",
        "الموضوعات",
    ),
    "assessment_records": (
        "assessment methods",
        "assessment activities",
        "methods of assessment",
        "طرق التقييم",
        "أساليب التقييم",
        "استراتيجيات التقويم",
        "استراتيجيات التقييم",
        "مواءمة التقييم",
        "assessment alignment",
        "alignment summary",
        "assessment alignment summary",
        "ملخص المواءمة",
        "ملخص مواءمة التقييم",
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
    raw_text: str | None = None
    raw_cells: tuple[str, ...] = ()
    reading_cells: tuple[str, ...] = ()
    cell_roles: tuple[str | None, ...] = ()
    table_section: str | None = None
    extraction_method: str = "direct_text"


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


_TRAILING_PLO = re.compile(
    rf"^(?P<text>.+?)\s+(?:(?:Knowledge|Skills?|Values?|"
    rf"المعارف?|المهارات?|القيم)\s+)?(?P<po>PLO\s*{_DIGITS})\s*$",
    re.IGNORECASE,
)
_TRAILING_TOPIC_HOURS = re.compile(
    rf"^(?P<text>.+?\D)\s+(?P<hours>{_NUMBER})\s*$",
    re.IGNORECASE,
)


def _split_trailing_clo_metadata(value: str) -> tuple[str, str | None]:
    """Separate a trailing domain/PLO token from the source-faithful CLO text.

    Compact TP-153 tables sometimes collapse the description, domain and PLO
    columns into one PDF text run (for example ``... constraints Knowledge
    PLO1``). The PLO is structured metadata, not part of the learning-outcome
    sentence. The source row remains preserved separately for audit.
    """

    compact = " ".join(value.split()).strip()
    match = _TRAILING_PLO.match(compact)
    if match is None:
        return compact, None
    text = match.group("text").rstrip(" -–—|,:;")
    text = re.sub(r"(?:\band\b|\bو\b)\s*$", "", text, flags=re.IGNORECASE).rstrip(
        " -–—|,:;"
    )
    return text, _canonical_po(match.group("po"))


def _split_trailing_topic_hours(value: str) -> tuple[str, float | None]:
    """Separate compact-table contact hours from topic text.

    A bare trailing number is accepted only in a topic row and only within a
    realistic course-hours range. This avoids stripping technical numbers from
    ordinary free text while handling rows such as ``Normalization 6``.
    """

    compact = " ".join(value.split()).strip().lstrip("|:-–— ")
    match = _TRAILING_TOPIC_HOURS.match(compact)
    if match is None:
        return compact, None
    hours = parse_localized_number(match.group("hours"))
    if hours <= 0 or hours > 60:
        return compact, None
    return match.group("text").rstrip(" -–—|,:;"), hours


def _assessment_clo_codes(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    normalized = normalize_arabic_for_matching(value)
    found: list[str] = []

    # Expand explicit inclusive ranges such as CLO1-CLO4 or CLO1-4.
    range_pattern = re.compile(
        rf"\bCLO\s*(?P<start>{_DIGITS})\s*[-–—]\s*(?:CLO\s*)?(?P<end>{_DIGITS})\b",
        re.IGNORECASE,
    )
    for match in range_pattern.finditer(normalized):
        start = int(to_ascii_digits(match.group("start")))
        end = int(to_ascii_digits(match.group("end")))
        step = 1 if end >= start else -1
        if abs(end - start) <= 50:
            for number in range(start, end + step, step):
                code = f"CLO{number}"
                if code not in found:
                    found.append(code)

    for match in _ASSESSMENT_CLO_CODE.finditer(normalized):
        code = _canonical_code("CLO", match.group(1))
        if code not in found:
            found.append(code)
    return tuple(found)


def _cells(text: str) -> list[str]:
    if "|" not in text and "\t" not in text and re.search(r"\s{2,}", text) is None:
        return []
    return [cell.strip() for cell in _CELL_SPLIT.split(text) if cell.strip()]


def _section_for_header(text: str) -> str | None:
    normalized = normalize_arabic_for_matching(text).casefold().strip(" :-–—()")
    for section, aliases in _SECTION_ALIASES.items():
        for alias in aliases:
            candidate = normalize_arabic_for_matching(alias).casefold().strip(" :-–—()")
            if normalized == candidate:
                return section
            # Bilingual headings commonly contain the same heading twice, e.g.
            # "مخرجات تعلم المقرر - Course Learning Outcomes".  Accept the
            # known heading at a boundary without treating arbitrary body text
            # that merely mentions a keyword as a section break.
            if normalized.startswith(candidate + " ") or normalized.endswith(" " + candidate):
                return section
    return None


def _header_role(value: str) -> str | None:
    normalized = normalize_arabic_for_matching(value).casefold()
    clo_header = _CLO_CODE.fullmatch(normalized.strip())
    if clo_header is not None:
        return f"clo:{_canonical_code('CLO', clo_header.group('number'))}"
    if (
        "assessment activity" in normalized
        or "نشاط التقييم" in normalized
        or normalized.strip(" /:-") in {
            "assessment",
            "assessment method",
            "method",
            "التقييم",
            "طريقة التقييم",
            "أسلوب التقييم",
        }
    ):
        return "method"
    if "weight" in normalized or "الوزن" in normalized or "النسبة" in normalized:
        return "percentage"
    if "notes" in normalized or "ملاحظات" in normalized:
        return "notes"
    if "related" in normalized and "clo" in normalized:
        return "related_clos"
    if "contact hours" in normalized or "ساعات الاتصال" in normalized:
        return "hours"
    if re.search(r"\btopic\b", normalized) or "الموضوع" in normalized:
        return "topic"
    if re.search(r"\bweek\b", normalized) or "الأسبوع" in normalized:
        return "week"
    if re.search(r"\bcode\b", normalized) or "رمز" in normalized:
        return "code"
    if "description" in normalized or "الوصف" in normalized:
        return "description"
    if "domain" in normalized or "المجال" in normalized:
        return "domain"
    return None


def _table_section(roles: tuple[str | None, ...]) -> str | None:
    role_set = {role for role in roles if role is not None}
    if {"code", "description"}.issubset(role_set):
        return "clos"
    if {"topic", "hours", "week"}.issubset(role_set):
        return "topics"
    if (
        {"method", "percentage", "week"}.issubset(role_set)
        or {"method", "related_clos"}.issubset(role_set)
        or ("method" in role_set and any(role.startswith("clo:") for role in role_set))
    ):
        return "assessment_records"
    return None


def _row_source_text(cells: tuple[str, ...]) -> str:
    return "\n--- cell ---\n".join(cells)


def _compact_cell(value: str) -> str:
    compact = " ".join(value.split()).strip(" /")
    return re.sub(r"([\u0600-\u06ff])\s+ة\b", r"\1ة", compact)


def _alignment_cell_selected(value: str) -> bool:
    """Accept only explicit positive alignment markers.

    Footer/header text must never become a positive CLO mapping merely because
    the extracted cell is non-empty.
    """
    normalized = normalize_arabic_for_matching(value).casefold().strip()
    if not normalized:
        return False
    compact = re.sub(r"\s+", "", normalized)
    return compact in {
        "✓", "✔", "☑", "x", "yes", "y", "true", "1", "نعم",
    }


def _clean_structured_assessment_method(reading: str, raw: str) -> str:
    """Remove page/footer fragments accidentally merged into a method cell."""
    raw_lines = [line.strip() for line in raw.splitlines() if line.strip()]
    kept: list[str] = []
    skip_numeric_after_page_of = False
    for raw_line in raw_lines:
        normalized = normalize_arabic_for_matching(raw_line).casefold().strip()
        if normalized in {"page of", "page"}:
            skip_numeric_after_page_of = True
            continue
        if skip_numeric_after_page_of and re.fullmatch(
            r"[0-9٠-٩۰-۹]+\s+[0-9٠-٩۰-۹]+", normalized
        ):
            skip_numeric_after_page_of = False
            continue
        skip_numeric_after_page_of = False
        if _looks_like_page_footer(raw_line):
            continue
        kept.append(raw_line)
    candidate = " ".join(kept).strip()
    if candidate:
        return _compact_cell(candidate)
    cleaned = _PAGE_FOOTER.sub("", reading)
    cleaned = re.sub(r"\bpage\s+of\b", "", cleaned, flags=re.IGNORECASE)
    return _compact_cell(cleaned)


def _restore_ltr_runs(reading: str, raw: str) -> str:
    restored = reading
    for raw_line in raw.splitlines():
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", raw_line)
        if len(tokens) < 2:
            continue
        original = " ".join(tokens)
        reversed_value = " ".join(reversed(tokens))
        restored = restored.replace(reversed_value, original)
    return restored


def _looks_like_page_footer(text: str) -> bool:
    normalized = normalize_arabic_for_matching(text)
    return _PAGE_FOOTER.search(normalized) is not None


def _looks_like_table_header(text: str) -> bool:
    normalized = normalize_arabic_for_matching(text).casefold()
    header_markers = (
        "clo النص",
        "clo code",
        "code description",
        "الرمز ناتج التعلم",
        "الرمز مخرج التعلم",
        "topic الموضوع",
        "topic code",
        "الرمز الموضوع",
        "أداة التقييم",
        "assessment method",
    )
    return any(marker in normalized for marker in header_markers)


def _display_text(value: str) -> str:
    """Normalize compatibility glyphs for canonical reading text only.

    The immutable PDF source remains available in ``raw_text``/evidence.  NFKC
    is important for Arabic presentation-form fonts used by some exported
    Course Specifications; it converts shaped glyphs into ordinary Unicode so
    matching and browser display remain stable.
    """

    return unicodedata.normalize("NFKC", value).strip()


def _union_geometry(first: Geometry | None, second: Geometry | None) -> Geometry | None:
    if first is None:
        return second
    if second is None:
        return first
    return Geometry(
        x0=min(first.x0, second.x0),
        top=min(first.top, second.top),
        x1=max(first.x1, second.x1),
        bottom=max(first.bottom, second.bottom),
    )


def _append_source_text(existing: str | None, line: CourseSpecificationLine) -> str | None:
    source = line.raw_text or line.text
    if not source:
        return existing
    return f"{existing}\n{source}" if existing else source


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
                    # Use geometry-derived logical reading order for parsing.
                    # ``page.extract_text`` remains only a quality signal/raw
                    # audit source; using it directly regresses Arabic and
                    # mixed RTL/LTR Course Specifications.
                    layout_lines = extract_layout_lines(page, page_number=page_number)
                    if layout_lines:
                        for layout_line in layout_lines:
                            source_lines.append(
                                CourseSpecificationLine(
                                    text=_display_text(layout_line.reading_text),
                                    raw_text=layout_line.raw_text,
                                    page_number=page_number,
                                    confidence=_FULL_CONFIDENCE,
                                    geometry=layout_line.geometry,
                                )
                            )
                    else:
                        page_lines = [line.strip() for line in text.splitlines() if line.strip()]
                        for line in page_lines:
                            geometry = _geometry_for_text(page, line)
                            source_lines.append(
                                CourseSpecificationLine(
                                    text=_display_text(line),
                                    raw_text=line,
                                    page_number=page_number,
                                    confidence=_direct_confidence(geometry),
                                    geometry=geometry,
                                )
                            )
                    try:
                        tables = page.find_tables()
                    except Exception:
                        tables = []
                    for table in tables:
                        extracted_rows = table.extract() or []
                        if not extracted_rows:
                            continue
                        header_cells = tuple(cell or "" for cell in extracted_rows[0])
                        header_roles = tuple(_header_role(cell) for cell in header_cells)
                        table_section = _table_section(header_roles)
                        if table_section is None:
                            continue
                        for row_index, row in enumerate(extracted_rows[1:], start=1):
                            raw_cells = tuple(cell or "" for cell in row)
                            if not any(cell.strip() for cell in raw_cells):
                                continue
                            row_object = table.rows[row_index]
                            reading_cells: list[str] = []
                            for cell_index, raw_cell in enumerate(raw_cells):
                                cell_bbox = (
                                    row_object.cells[cell_index]
                                    if cell_index < len(row_object.cells)
                                    else None
                                )
                                if cell_bbox is None:
                                    reading_cells.append(_compact_cell(raw_cell))
                                    continue
                                cell_x0, cell_top, cell_x1, cell_bottom = cell_bbox
                                cell_lines = extract_layout_lines(
                                    page,
                                    page_number=page_number,
                                    bbox=(
                                        float(cell_x0),
                                        float(cell_top),
                                        float(cell_x1),
                                        float(cell_bottom),
                                    ),
                                )
                                reading = "\n".join(
                                    line.reading_text for line in cell_lines
                                ).strip() or _compact_cell(raw_cell)
                                reading_cells.append(_display_text(_restore_ltr_runs(reading, raw_cell)))
                            x0, top, x1, bottom = row_object.bbox
                            row_geometry = Geometry(
                                float(x0),
                                float(top),
                                float(x1),
                                float(bottom),
                            )
                            source_lines.append(
                                CourseSpecificationLine(
                                    text=" | ".join(reading_cells),
                                    page_number=page_number,
                                    confidence=0.95,
                                    geometry=row_geometry,
                                    raw_cells=raw_cells,
                                    reading_cells=tuple(reading_cells),
                                    cell_roles=header_roles,
                                    table_section=table_section,
                                )
                            )
                    detection = detect_text_language(
                        "\n".join(item.text for item in source_lines if item.page_number == page_number)
                        or text
                    )
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

            # Structured rows are authoritative even when pdfplumber merges a
            # page footer into the last table row. Parse the row first and
            # sanitize individual cells instead of discarding the whole row.
            if line.table_section is not None:
                table_seen = True
                if line.table_section == "clos":
                    clo = self._parse_structured_clo(line)
                    if clo is not None:
                        clos.append(clo)
                elif line.table_section == "topics":
                    topic = self._parse_structured_topic(line)
                    if topic is not None:
                        topics.append(topic)
                elif line.table_section == "assessment_records":
                    assessment = self._parse_structured_assessment(line)
                    if assessment is not None:
                        assessment_records.append(assessment)
                continue

            if _looks_like_page_footer(source):
                current_section = None
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
                continue

            # Some Course Specifications wrap a CLO/topic description onto a
            # following visual line without repeating the code.  Preserve the
            # continuation only while we remain in that section and only when
            # the line is not a known column/header row.
            if current_section == "clos" and clos and not _looks_like_table_header(source):
                previous = clos[-1]
                if previous.page_number == line.page_number:
                    clos[-1] = replace(
                        previous,
                        text=f"{previous.text.rstrip()} {source.lstrip()}".strip(),
                        confidence=min(previous.confidence, _scaled_confidence(line, 0.95)),
                        geometry=_union_geometry(previous.geometry, line.geometry),
                        source_text=previous.source_text,
                    )
                    continue
            if current_section == "topics" and topics and not _looks_like_table_header(source):
                previous = topics[-1]
                if previous.page_number == line.page_number:
                    topics[-1] = replace(
                        previous,
                        text=f"{previous.text.rstrip()} {source.lstrip()}".strip(),
                        confidence=min(previous.confidence, _scaled_confidence(line, 0.95)),
                        geometry=_union_geometry(previous.geometry, line.geometry),
                        source_text=previous.source_text,
                    )

        review_warnings: list[CourseSpecificationWarning] = []
        review_warnings.extend(self._duplicate_warnings(clos, "CLO"))
        review_warnings.extend(self._duplicate_warnings(topics, "topic"))
        clos = self._dedupe_clos(clos)
        topics = self._dedupe_topics(topics)
        assessment_records = self._dedupe_assessments(assessment_records)
        course_fields = self._dedupe_course_fields(course_fields)
        low_confidence_records = (
            ("CLO", [(record.confidence, record.page_number) for record in clos]),
            ("topic", [(record.confidence, record.page_number) for record in topics]),
            (
                "assessment record",
                [(record.confidence, record.page_number) for record in assessment_records],
            ),
            (
                "course field",
                [(record.confidence, record.page_number) for record in course_fields],
            ),
        )
        for collection_name, confidence_records in low_confidence_records:
            for confidence, page_number in confidence_records:
                if confidence < _LOW_CONFIDENCE_REVIEW:
                    review_warnings.append(
                        CourseSpecificationWarning(
                            code="low_confidence_record",
                            page_number=page_number,
                            message=(
                                f"A {collection_name} has low extraction confidence and "
                                "should be checked against the Course Specification."
                            ),
                            confidence=confidence,
                        )
                    )

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
            review_warnings=review_warnings,
        )

    @staticmethod
    def _duplicate_warnings(
        records: list[ExtractedClo] | list[ExtractedTopic],
        label: str,
    ) -> list[CourseSpecificationWarning]:
        by_code: dict[str, list[ExtractedClo | ExtractedTopic]] = {}
        for record in records:
            code = record.code
            if code is not None:
                by_code.setdefault(code, []).append(record)
        return [
            CourseSpecificationWarning(
                code="duplicate_conflicting_code",
                page_number=items[0].page_number,
                message=f"Conflicting source rows use the same {label} code {code}.",
                confidence=min(item.confidence for item in items),
            )
            for code, items in by_code.items()
            if len({item.text for item in items}) > 1
        ]

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
            clean_text, trailing_po = _split_trailing_clo_metadata(cells[1])
            return ExtractedClo(
                code=_canonical_code("CLO", code_match.group("number")),
                text=clean_text,
                program_outcome_reference=_canonical_po(po) or trailing_po,
                page_number=line.page_number,
                confidence=_scaled_confidence(line, 0.9),
                geometry=line.geometry,
            )

        explicit = _CLO_EXPLICIT.match(line.text.strip())
        if explicit is not None:
            clean_text, trailing_po = _split_trailing_clo_metadata(explicit.group("text"))
            return ExtractedClo(
                code=_canonical_code("CLO", explicit.group("number")),
                text=clean_text,
                program_outcome_reference=_canonical_po(explicit.group("po")) or trailing_po,
                page_number=line.page_number,
                confidence=_scaled_confidence(line, 1.0),
                geometry=line.geometry,
            )

        if current_section == "clos":
            inline_codes = list(_CLO_INLINE_CODE.finditer(line.text))
            if len(inline_codes) == 1 and not _looks_like_table_header(line.text):
                match = inline_codes[0]
                text = (line.text[: match.start()] + " " + line.text[match.end() :]).strip(" -–—|:;,. ")
                if text:
                    clean_text, trailing_po = _split_trailing_clo_metadata(text)
                    return ExtractedClo(
                        code=_canonical_code("CLO", match.group("number")),
                        text=clean_text,
                        program_outcome_reference=trailing_po,
                        page_number=line.page_number,
                        confidence=_scaled_confidence(line, 0.95),
                        geometry=line.geometry,
                    )

        return None

    @staticmethod
    def _role_cells(line: CourseSpecificationLine) -> dict[str, tuple[str, str]]:
        return {
            role: (line.reading_cells[index], line.raw_cells[index])
            for index, role in enumerate(line.cell_roles)
            if role is not None and index < len(line.reading_cells) and index < len(line.raw_cells)
        }

    def _parse_structured_clo(self, line: CourseSpecificationLine) -> ExtractedClo | None:
        cells = self._role_cells(line)
        code_value = _compact_cell(cells.get("code", ("", ""))[0])
        code_match = _CLO_CODE.match(code_value)
        description = _compact_cell(cells.get("description", ("", ""))[0])
        if code_match is None or not description:
            return None
        clean_text, trailing_po = _split_trailing_clo_metadata(description)
        return ExtractedClo(
            code=_canonical_code("CLO", code_match.group("number")),
            text=clean_text,
            program_outcome_reference=trailing_po,
            page_number=line.page_number,
            confidence=_scaled_confidence(line, 0.98),
            geometry=line.geometry,
            source_text=_row_source_text(line.raw_cells),
            extraction_method=line.extraction_method,
        )

    def _parse_structured_topic(self, line: CourseSpecificationLine) -> ExtractedTopic | None:
        cells = self._role_cells(line)
        code_value = _compact_cell(cells.get("code", ("", ""))[0])
        code_match = _TOPIC_CODE.match(code_value)
        text = _compact_cell(cells.get("topic", ("", ""))[0])
        hours_value = normalize_arabic_for_matching(cells.get("hours", ("", ""))[0])
        hours_match = re.search(_NUMBER, hours_value)
        if not text:
            return None
        clean_text, trailing_hours = _split_trailing_topic_hours(text)
        explicit_hours = (
            parse_localized_number(hours_match.group()) if hours_match is not None else None
        )
        return ExtractedTopic(
            code=(
                _canonical_code("T", code_match.group("number"))
                if code_match is not None
                else None
            ),
            text=clean_text,
            expected_hours=explicit_hours if explicit_hours is not None else trailing_hours,
            page_number=line.page_number,
            confidence=_scaled_confidence(line, 0.98),
            geometry=line.geometry,
            source_text=_row_source_text(line.raw_cells),
            extraction_method=line.extraction_method,
        )

    def _parse_structured_assessment(
        self, line: CourseSpecificationLine
    ) -> ExtractedAssessmentRecord | None:
        cells = self._role_cells(line)
        method_reading, method_raw = cells.get("method", ("", ""))
        method = _clean_structured_assessment_method(method_reading, method_raw)
        notes = _compact_cell(cells.get("notes", ("", ""))[0])
        related_clos = _compact_cell(cells.get("related_clos", ("", ""))[0])
        matrix_clos = [
            role.split(":", 1)[1]
            for role, (reading, raw) in cells.items()
            if role.startswith("clo:") and _alignment_cell_selected(reading or raw)
        ]
        related_clo_codes = tuple(
            dict.fromkeys([*_assessment_clo_codes(related_clos or notes), *matrix_clos])
        )
        percentage_value = normalize_arabic_for_matching(cells.get("percentage", ("", ""))[0])
        percentage_match = re.search(_NUMBER, percentage_value)
        if not method:
            return None
        return ExtractedAssessmentRecord(
            method=method,
            activity=notes or None,
            percentage=(
                parse_localized_number(percentage_match.group())
                if percentage_match is not None
                else None
            ),
            page_number=line.page_number,
            confidence=_scaled_confidence(line, 0.98),
            geometry=line.geometry,
            source_text=_row_source_text(line.raw_cells),
            extraction_method=line.extraction_method,
            related_clo_codes=related_clo_codes,
        )

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
            clean_text, trailing_hours = _split_trailing_topic_hours(text)
            explicit_hours = parse_localized_number(hours) if hours else None
            return ExtractedTopic(
                code=_canonical_code("T", number),
                text=clean_text,
                expected_hours=explicit_hours if explicit_hours is not None else trailing_hours,
                page_number=line.page_number,
                confidence=_scaled_confidence(line, 1.0),
                geometry=line.geometry,
            )

        if current_section == "topics" and not _looks_like_table_header(line.text):
            inline_codes = list(_TOPIC_INLINE_CODE.finditer(line.text))
            if len(inline_codes) == 1:
                match = inline_codes[0]
                text = (line.text[: match.start()] + " " + line.text[match.end() :]).strip(" -–—|:;,. ")
                if text:
                    clean_text, trailing_hours = _split_trailing_topic_hours(text)
                    return ExtractedTopic(
                        code=_canonical_code("T", match.group("number")),
                        text=clean_text,
                        expected_hours=trailing_hours,
                        page_number=line.page_number,
                        confidence=_scaled_confidence(line, 0.95),
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
        clean_text, trailing_hours = _split_trailing_topic_hours(cells[1])
        explicit_hours = parse_localized_number(hours) if hours else None
        return ExtractedTopic(
            code=_canonical_code("T", code_match.group("number")),
            text=clean_text,
            expected_hours=explicit_hours if explicit_hours is not None else trailing_hours,
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

        if current_section == "assessment_records":
            inline_clos = _assessment_clo_codes(source)
            if inline_clos:
                method = _ASSESSMENT_CLO_CODE.sub("", source)
                method = re.sub(r"[\s,،;|:/\-–—]+", " ", method).strip()
                header_name = normalize_arabic_for_matching(method).casefold().strip()
                if header_name in {
                    "assessment", "assessments", "assessment activity",
                    "assessment method", "method", "التقييم", "التقويم",
                    "نشاط التقييم", "طريقة التقييم", "أسلوب التقييم",
                }:
                    return []
                if method:
                    return [
                        ExtractedAssessmentRecord(
                            method=method,
                            activity=None,
                            percentage=None,
                            page_number=line.page_number,
                            confidence=_scaled_confidence(line, 0.9),
                            geometry=line.geometry,
                            source_text=line.raw_text or line.text,
                            extraction_method=line.extraction_method,
                            related_clo_codes=inline_clos,
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
        """Keep the most source-faithful view when multiple parsers see one CLO.

        Layout text and a detected table can describe the same row.  A slightly
        higher line confidence must not beat a structured candidate that keeps
        the complete raw source row, otherwise wrapped bilingual text can absorb
        neighbouring page text and lose the reviewer-copy provenance.
        """

        def rank(record: ExtractedClo) -> tuple[bool, bool, bool, float, int]:
            return (
                bool(record.source_text),
                bool(record.source_text and "\n" in record.source_text),
                record.geometry is not None,
                record.confidence,
                len(record.text.strip()),
            )

        by_code: dict[str, ExtractedClo] = {}
        for record in records:
            current = by_code.get(record.code)
            if current is None or rank(record) > rank(current):
                by_code[record.code] = record
        return list(by_code.values())

    @staticmethod
    def _dedupe_topics(records: list[ExtractedTopic]) -> list[ExtractedTopic]:
        """Merge duplicate parser/recovery views of the same source topic.

        A coded table row (``T2``) and an uncoded recovery of that exact row
        used to receive unrelated keys (code vs. text) and both reached review.
        Deduplication now uses source identity first and preserves conflicting
        explicit codes rather than silently collapsing genuinely distinct rows.
        """

        def normalized_text(record: ExtractedTopic) -> str:
            return " ".join(
                normalize_arabic_for_matching(record.text).casefold().split()
            )

        def same_source(left: ExtractedTopic, right: ExtractedTopic) -> bool:
            left_code = left.code.casefold() if left.code else None
            right_code = right.code.casefold() if right.code else None
            if left_code and right_code and left_code != right_code:
                return False
            if normalized_text(left) == normalized_text(right):
                return True
            if (
                left.page_number != right.page_number
                or left.geometry is None
                or right.geometry is None
            ):
                return False
            left_center = (
                (left.geometry.x0 + left.geometry.x1) / 2,
                (left.geometry.top + left.geometry.bottom) / 2,
            )
            right_center = (
                (right.geometry.x0 + right.geometry.x1) / 2,
                (right.geometry.top + right.geometry.bottom) / 2,
            )
            same_region = (
                abs(left_center[0] - right_center[0]) <= 24
                and abs(left_center[1] - right_center[1]) <= 18
            )
            if not same_region:
                return False
            left_text = normalized_text(left)
            right_text = normalized_text(right)
            return bool(
                left_text
                and right_text
                and (left_text in right_text or right_text in left_text)
            )

        def preferred(left: ExtractedTopic, right: ExtractedTopic) -> ExtractedTopic:
            ranked = sorted(
                (left, right),
                key=lambda item: (
                    bool(item.source_text),
                    item.code is not None,
                    item.expected_hours is not None,
                    item.geometry is not None,
                    item.confidence,
                    len(item.text.strip()),
                ),
                reverse=True,
            )
            best = ranked[0]
            other = ranked[1]
            return replace(
                best,
                code=best.code or other.code,
                expected_hours=(
                    best.expected_hours
                    if best.expected_hours is not None
                    else other.expected_hours
                ),
                source_text=best.source_text or other.source_text,
            )

        merged: list[ExtractedTopic] = []
        for record in records:
            duplicate_index = next(
                (index for index, current in enumerate(merged) if same_source(current, record)),
                None,
            )
            if duplicate_index is None:
                merged.append(record)
                continue
            merged[duplicate_index] = preferred(merged[duplicate_index], record)

        # A second exact-code pass handles duplicate rows extracted through two
        # table paths even when one representation contains harmless extra text.
        by_code: dict[str, int] = {}
        final: list[ExtractedTopic] = []
        for record in merged:
            if not record.code:
                final.append(record)
                continue
            key = record.code.casefold()
            existing_index = by_code.get(key)
            if existing_index is None:
                by_code[key] = len(final)
                final.append(record)
            else:
                final[existing_index] = preferred(final[existing_index], record)
        return final

    @staticmethod
    def _dedupe_assessments(
        records: list[ExtractedAssessmentRecord],
    ) -> list[ExtractedAssessmentRecord]:
        by_key: dict[str, ExtractedAssessmentRecord] = {}
        for record in records:
            key = normalize_arabic_for_matching(record.method).casefold()
            current = by_key.get(key)
            if current is None:
                by_key[key] = record
                continue
            preferred = record if record.confidence > current.confidence else current
            other = current if preferred is record else record
            by_key[key] = replace(
                preferred,
                activity=preferred.activity or other.activity,
                percentage=preferred.percentage if preferred.percentage is not None else other.percentage,
                source_text=preferred.source_text or other.source_text,
                related_clo_codes=tuple(dict.fromkeys([*current.related_clo_codes, *record.related_clo_codes])),
            )
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
