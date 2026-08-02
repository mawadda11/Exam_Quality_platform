"""Conservative bilingual extraction of supporting materials and explicit references."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pdfplumber.page import Page

from app.core.domain import (
    ReferenceTargetType,
    SupportingAnnotationType,
    SupportingMaterialType,
)
from app.services.extraction.pdf_layout import PdfLayoutLine
from app.services.extraction.text_normalization import (
    normalize_arabic_for_matching,
    to_ascii_digits,
)
from app.services.extraction.types import (
    ExtractedDocumentReference,
    ExtractedSupportingAnnotation,
    ExtractedSupportingMaterial,
    Geometry,
)

_DIGITS = r"[0-9٠-٩۰-۹]+"
_KIND = (
    r"(?P<kind>Fig(?:ure)?|Table|Code(?:\s+(?:Block|Listing))?|"
    r"الشكل|شكل|الجدول|جدول|الشيفرة|شفرة|الكود|مقطع\s+الشفرة)"
)
_LABEL = re.compile(
    rf"^\s*[-–—]?\s*{_KIND}\s*(?:No\.?|Number|رقم)?\s*(?P<number>{_DIGITS})"
    r"\s*(?P<separator>[:.\-–—])?\s*(?P<caption>.*)$",
    re.IGNORECASE,
)
_MATERIAL_REFERENCE = re.compile(
    rf"{_KIND}\s*(?:No\.?|Number|رقم)?\s*(?P<number>{_DIGITS})",
    re.IGNORECASE,
)
_VISUAL_ARABIC_REFERENCE = re.compile(
    rf"(?P<number>{_DIGITS})\s*"
    rf"(?P<kind>لكشلا|لكش|لودجلا|لودج|دوكلا|دوك)",
    re.IGNORECASE,
)
_GENERIC_DIAGRAM_REFERENCE = re.compile(
    r"(?:diagram\s+(?:below|shown|following)|"
    r"(?:المخطط|الشكل)\s+(?:أدناه|التالي|الموضح))",
    re.IGNORECASE,
)
_QUESTION_REFERENCE = re.compile(
    rf"(?:see|refer\s+to|as\s+in|راجع|انظر(?:\s+إلى)?)\s+"
    rf"(?P<kind>Question|Q|السؤال|س)\s*(?P<number>{_DIGITS})",
    re.IGNORECASE,
)
_CODE_LINE = re.compile(
    r"^\s*(?:```|(?:async\s+)?def\s+\w+\s*\(.*|class\s+\w+.*:|"
    r"SELECT\s+.+\s+FROM\s+|for\s*\(.+\)|if\s*\(.+\)|print\s*\(.*|"
    r"(?:self\.)?[A-Za-z_]\w*(?:\.\w+)*\s*(?:=|\().*)$",
    re.IGNORECASE,
)
_ARABIC_CHARACTER = re.compile(r"[\u0600-\u06ff]")
_LOGICAL_ARABIC_LABEL = re.compile(r"^\s*(?:الشكل|الجدول|الكود)\s*[0-9٠-٩۰-۹]+\s*(?::|$)")
_ENGLISH_LABELED_CAPTION = re.compile(
    r"(?:Fig(?:ure)?|Table|Code(?:\s+(?:Block|Listing))?)"
    r"\s*(?:No\.?|Number)?\s*[0-9]+\s*[:.\-–—]\s*"
    r"(?P<caption>[^\u0600-\u06ff]*)",
    re.IGNORECASE,
)
_LATIN_LETTER = re.compile(r"[A-Za-z]")
_ARABIC_PRESENTATION_KIND = {
    SupportingMaterialType.FIGURE.value: "الشكل",
    SupportingMaterialType.TABLE.value: "الجدول",
    SupportingMaterialType.CODE_BLOCK.value: "الكود",
}


def _geometry(value: dict[str, Any]) -> Geometry:
    return Geometry(
        x0=float(value["x0"]),
        top=float(value["top"]),
        x1=float(value["x1"]),
        bottom=float(value["bottom"]),
    )


def _search_geometry(page: Page, text: str) -> Geometry | None:
    try:
        matches = page.search(re.escape(text))
    except Exception:
        return None
    return _geometry(matches[0]) if matches else None


def _kind(value: str) -> SupportingMaterialType:
    normalized = normalize_arabic_for_matching(value).casefold().replace(".", "")
    if normalized.startswith(("fig", "شكل", "الشكل", "لكش", "لكشلا")):
        return SupportingMaterialType.FIGURE
    if normalized.startswith(("table", "جدول", "الجدول", "لودج", "لودجلا")):
        return SupportingMaterialType.TABLE
    return SupportingMaterialType.CODE_BLOCK


def _target_type(value: SupportingMaterialType) -> ReferenceTargetType:
    return ReferenceTargetType(value.value)


def normalize_explicit_label(kind: str, number: str) -> str:
    canonical_kind = _kind(kind).value
    canonical_number = str(int(to_ascii_digits(number)))
    return f"{canonical_kind}:{canonical_number}"


def normalize_question_label(number: str) -> str:
    return f"question:{int(to_ascii_digits(number))}"


def normalize_target_label(target_type: ReferenceTargetType, value: str) -> str:
    digits = re.search(_DIGITS, value)
    if digits is None:
        return normalize_arabic_for_matching(value).casefold().strip()
    if target_type is ReferenceTargetType.QUESTION:
        return normalize_question_label(digits.group())
    return f"{target_type.value}:{int(to_ascii_digits(digits.group()))}"


def normalize_annotation_label(value: str) -> str | None:
    match = _LABEL.match(value)
    if match is None:
        return None
    return normalize_explicit_label(match.group("kind"), match.group("number"))


def logical_annotation_text(original_text: str, normalized_label: str | None) -> str:
    """Return a bidi-safe logical presentation while leaving source text untouched.

    Some PDFs encode Arabic glyphs in visual order while adjacent English remains
    logical. Reversing the complete string would corrupt English phrases and
    identifiers, so only the Arabic label is reconstructed from its normalized
    audit label and the already-logical Latin caption is retained verbatim.
    """

    source = " ".join(original_text.split()).strip()
    if not source or _ARABIC_CHARACTER.search(source) is None:
        return source
    if _LOGICAL_ARABIC_LABEL.match(source):
        return source

    kind_value: str | None = None
    number: str | None = None
    if normalized_label:
        kind_value, separator, number_value = normalized_label.partition(":")
        if separator and number_value.isdigit():
            number = number_value
        else:
            kind_value = None
    arabic_kind = _ARABIC_PRESENTATION_KIND.get(kind_value or "")
    if arabic_kind is None or number is None:
        return source

    labeled_caption = _ENGLISH_LABELED_CAPTION.search(source)
    if labeled_caption is not None:
        caption = labeled_caption.group("caption")
    else:
        first_arabic = _ARABIC_CHARACTER.search(source)
        caption = source[: first_arabic.start()] if first_arabic is not None else ""
        caption = re.sub(
            r"^\s*[-–—]?\s*(?:Fig(?:ure)?|Table|Code(?:\s+(?:Block|Listing))?)"
            r"\s*(?:No\.?|Number)?\s*[0-9]+\s*[:.\-–—]?\s*",
            "",
            caption,
            flags=re.IGNORECASE,
        )
    if not caption.strip() and _LATIN_LETTER.search(source) is None:
        clusters: list[str] = []
        for character in source:
            if unicodedata.combining(character) and clusters:
                clusters[-1] += character
            else:
                clusters.append(character)
        logical_source = "".join(reversed(clusters))
        logical_source = re.sub(
            r"[0-9٠-٩۰-۹]+",
            lambda match: match.group(0)[::-1],
            logical_source,
        )
        logical_match = _LABEL.match(logical_source)
        caption = (
            logical_match.group("caption").strip() if logical_match is not None else logical_source
        )
    caption = caption.strip(" \t\r\n:.-–—")
    label = f"{arabic_kind} {number}"
    return f"{label}: {caption}" if caption else label


def _vertical_distance(left: Geometry | None, right: Geometry | None) -> float | None:
    if left is None or right is None:
        return None
    if left.bottom < right.top:
        return right.top - left.bottom
    if right.bottom < left.top:
        return left.top - right.bottom
    return 0.0


@dataclass(frozen=True)
class PageStructuredEvidence:
    materials: list[ExtractedSupportingMaterial]
    annotations: list[ExtractedSupportingAnnotation]


def _line_text(line: str | PdfLayoutLine) -> str:
    return line.reading_text if isinstance(line, PdfLayoutLine) else line


def _line_source_text(line: str | PdfLayoutLine) -> str:
    return line.raw_text if isinstance(line, PdfLayoutLine) else line


def _line_geometry(page: Page, line: str | PdfLayoutLine) -> Geometry | None:
    return line.geometry if isinstance(line, PdfLayoutLine) else _search_geometry(page, line)


def is_code_line(value: str) -> bool:
    # Question headers such as ``Q1 (8 marks).`` superficially resemble a
    # function call (identifier followed by parentheses). They must remain
    # question text and must never create a synthetic code-block material.
    normalized = normalize_arabic_for_matching(value).strip()
    if re.match(
        r"^(?:Q\s*\d+|Question\s+(?:No\.?\s*)?\d+|س\s*\d+|السؤال\s+)",
        normalized,
        re.IGNORECASE,
    ):
        return False
    return _CODE_LINE.match(value) is not None


def _is_meaningful_table(rows: list[list[str | None]]) -> bool:
    row_count = len(rows)
    column_count = max((len(row) for row in rows), default=0)
    nonempty = sum(bool((cell or "").strip()) for row in rows for cell in row)
    return row_count >= 2 and column_count >= 2 and nonempty >= 4


def extract_page_materials(
    page: Page,
    lines: Sequence[str | PdfLayoutLine],
    *,
    page_number: int,
    extraction_method: str,
    detect_embedded_assets: bool = True,
) -> PageStructuredEvidence:
    materials: list[ExtractedSupportingMaterial] = []
    annotations: list[ExtractedSupportingAnnotation] = []

    for index, image in enumerate(page.images if detect_embedded_assets else []):
        image_geometry = Geometry(
            x0=float(image["x0"]),
            top=float(image["top"]),
            x1=float(image["x1"]),
            bottom=float(image["bottom"]),
        )
        materials.append(
            ExtractedSupportingMaterial(
                local_key=f"p{page_number}:figure:{index}",
                material_type=SupportingMaterialType.FIGURE,
                page_number=page_number,
                source_text="",
                confidence=1.0,
                geometry=image_geometry,
                extraction_method=extraction_method,
            )
        )

    if detect_embedded_assets:
        try:
            tables = page.find_tables()
        except Exception:
            tables = []
    else:
        tables = []
    for index, table in enumerate(tables):
        x0, top, x1, bottom = table.bbox
        rows = table.extract() or []
        if not _is_meaningful_table(rows):
            continue
        source_text = "\n".join(
            " | ".join((cell or "").strip() for cell in row) for row in rows
        ).strip()
        materials.append(
            ExtractedSupportingMaterial(
                local_key=f"p{page_number}:table:{index}",
                material_type=SupportingMaterialType.TABLE,
                page_number=page_number,
                source_text=source_text,
                confidence=0.95,
                geometry=Geometry(float(x0), float(top), float(x1), float(bottom)),
                extraction_method=extraction_method,
            )
        )

    code_lines = [line for line in lines if is_code_line(_line_text(line))]
    if len(code_lines) >= 2 or any(
        _line_text(line).strip().startswith("```") for line in code_lines
    ):
        geometries = [_line_geometry(page, line) for line in code_lines]
        present = [item for item in geometries if item is not None]
        code_geometry = (
            Geometry(
                min(item.x0 for item in present),
                min(item.top for item in present),
                max(item.x1 for item in present),
                max(item.bottom for item in present),
            )
            if present
            else None
        )
        materials.append(
            ExtractedSupportingMaterial(
                local_key=f"p{page_number}:code:0",
                material_type=SupportingMaterialType.CODE_BLOCK,
                page_number=page_number,
                source_text="\n".join(_line_source_text(line) for line in code_lines),
                confidence=0.9 if code_geometry is not None else 0.65,
                geometry=code_geometry,
                extraction_method=extraction_method,
            )
        )

    for index, line in enumerate(lines):
        reading_text = _line_text(line)
        source_text = _line_source_text(line)
        match = _LABEL.match(source_text) or _LABEL.match(reading_text)
        if match is None:
            continue
        material_type = _kind(match.group("kind"))
        normalized = normalize_explicit_label(match.group("kind"), match.group("number"))
        label_geometry = _line_geometry(page, line)
        candidates = [item for item in materials if item.material_type is material_type]
        ranked = sorted(
            (
                (distance, item)
                for item in candidates
                if (distance := _vertical_distance(label_geometry, item.geometry)) is not None
            ),
            key=lambda value: value[0],
        )
        linked_key = (
            ranked[0][1].local_key
            if ranked and ranked[0][0] <= 48 and (len(ranked) == 1 or ranked[0][0] < ranked[1][0])
            else None
        )
        annotations.append(
            ExtractedSupportingAnnotation(
                local_key=f"p{page_number}:label:{index}",
                material_local_key=linked_key,
                annotation_type=SupportingAnnotationType.LABEL,
                original_text=match.group(0).strip(),
                normalized_label=normalized,
                page_number=page_number,
                confidence=1.0 if label_geometry is not None else 0.6,
                geometry=label_geometry,
                extraction_method=extraction_method,
            )
        )
        caption = match.group("caption").strip()
        if caption:
            annotations.append(
                ExtractedSupportingAnnotation(
                    local_key=f"p{page_number}:caption:{index}",
                    material_local_key=linked_key,
                    annotation_type=SupportingAnnotationType.CAPTION,
                    original_text=caption,
                    normalized_label=normalized,
                    page_number=page_number,
                    confidence=1.0 if label_geometry is not None else 0.6,
                    geometry=label_geometry,
                    extraction_method=extraction_method,
                )
            )
    return PageStructuredEvidence(materials=materials, annotations=annotations)


def extract_question_references(
    *,
    text: str,
    question_number_label: str,
    page_number: int,
    geometry: Geometry | None,
    confidence: float,
    extraction_method: str,
) -> list[ExtractedDocumentReference]:
    references: list[ExtractedDocumentReference] = []
    seen: set[str] = set()
    for index, match in enumerate(_MATERIAL_REFERENCE.finditer(text)):
        normalized = normalize_explicit_label(match.group("kind"), match.group("number"))
        if normalized in seen:
            continue
        seen.add(normalized)
        references.append(
            ExtractedDocumentReference(
                local_key=f"{question_number_label}:material-ref:{index}",
                target_type=_target_type(_kind(match.group("kind"))),
                original_text=match.group(0),
                target_label=match.group(0),
                normalized_target_label=normalized,
                page_number=page_number,
                confidence=confidence,
                geometry=geometry,
                extraction_method=extraction_method,
                question_number_label=question_number_label,
            )
        )
    visual_offset = len(references)
    for index, match in enumerate(_VISUAL_ARABIC_REFERENCE.finditer(text)):
        normalized = normalize_explicit_label(match.group("kind"), match.group("number"))
        if normalized in seen:
            continue
        seen.add(normalized)
        references.append(
            ExtractedDocumentReference(
                local_key=f"{question_number_label}:visual-material-ref:{visual_offset + index}",
                target_type=_target_type(_kind(match.group("kind"))),
                original_text=match.group(0),
                target_label=match.group(0),
                normalized_target_label=normalized,
                page_number=page_number,
                confidence=confidence,
                geometry=geometry,
                extraction_method=extraction_method,
                question_number_label=question_number_label,
            )
        )
    generic = _GENERIC_DIAGRAM_REFERENCE.search(text)
    if generic is not None and not any(
        reference.target_type is ReferenceTargetType.FIGURE for reference in references
    ):
        references.append(
            ExtractedDocumentReference(
                local_key=f"{question_number_label}:generic-diagram-ref:0",
                target_type=ReferenceTargetType.FIGURE,
                original_text=generic.group(0),
                target_label=generic.group(0),
                normalized_target_label="figure:unlabeled",
                page_number=page_number,
                confidence=min(confidence, 0.8),
                geometry=geometry,
                extraction_method=extraction_method,
                question_number_label=question_number_label,
            )
        )
    for index, match in enumerate(_QUESTION_REFERENCE.finditer(text)):
        normalized = normalize_question_label(match.group("number"))
        references.append(
            ExtractedDocumentReference(
                local_key=f"{question_number_label}:question-ref:{index}",
                target_type=ReferenceTargetType.QUESTION,
                original_text=match.group(0),
                target_label=match.group(0),
                normalized_target_label=normalized,
                page_number=page_number,
                confidence=confidence,
                geometry=geometry,
                extraction_method=extraction_method,
                question_number_label=question_number_label,
            )
        )
    return references
