"""Conservative bilingual extraction of supporting materials and explicit references."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, replace
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
    ExtractedTableCell,
    Geometry,
)

_DIGITS = r"[0-9٠-٩۰-۹]+"
_KIND = (
    r"(?P<kind>Fig(?:ure)?|Table|Code(?:\s+(?:Block|Listing))?|"
    r"الشكل|شكل|الجدول|جدول|الشيفرة|شفرة|الكود|مقطع\s+الشفرة)"
)
_LABEL = re.compile(
    rf"^\s*[-–—]?\s*{_KIND}\s*(?:No\.?|Number|رقم)?\s*[:：]?\s*(?P<number>{_DIGITS})"
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
    r"(?:diagram|figure|chart|illustration|الرسم|المخطط|الشكل)", re.IGNORECASE
)
_GENERIC_TABLE_REFERENCE = re.compile(r"(?:table|grid|الجدول|جدول)", re.IGNORECASE)
_GENERIC_CODE_REFERENCE = re.compile(
    r"(?:code|listing|snippet|source\s+code|الكود|الشفرة|شفرة|مقطع\s+الشفرة)", re.IGNORECASE
)
_DEICTIC_CUE = re.compile(
    r"(?:below|above|following|previous|shown|provided|attached|next|preceding|"
    r"أدناه|أعلاه|التالي|السابق|الموضح|المبين|المرفق|الآتي|الاتي)", re.IGNORECASE
)
_QUESTION_REFERENCE = re.compile(
    rf"(?:see|refer\s+to|as\s+in|راجع|انظر(?:\s+إلى)?)\s+"
    rf"(?P<kind>Question|Q|السؤال|س)\s*(?P<number>{_DIGITS})",
    re.IGNORECASE,
)
_CODE_LINE = re.compile(
    r"^\s*(?:```|(?:async\s+)?def\s+\w+\s*\(.*|class\s+\w+.*:|"
    r"(?:async\s+)?function\s+[A-Za-z_$][\w$]*\s*\([^)]*\)\s*\{?|"
    r"(?:const|let|var|final|static|int|long|float|double|boolean|bool|char|String|str|auto)\s+"
    r"[A-Za-z_$][\w$]*(?:\s*:\s*[^=]+)?\s*=\s*.+|"
    r"//.*|fetch\s*\(.*|\.\s*then\s*\(.*|"
    r"SELECT\s+.+\s+FROM\s+|for\s*\(.+\)\s*\{?|if\s*\(.+\)\s*\{?|while\s*\(.+\)\s*\{?|"
    r"print\s*\(.*\)\s*;?|return(?:\s+.+)?|[{}]+|"
    r"[\]\})]+\s*[,;)]*|"
    r"[A-Za-z_]\w*\s*:\s*.+[,}]?|"
    r"[A-Za-z_$][\w$]*(?:\([^)]*\)|\.[A-Za-z_$][\w$]*)+\s*=\s*.+|"
    r"(?:self\.)?[A-Za-z_]\w*(?:\.\w+)*\s*=\s*.+|"
    r"(?:self\.)?[A-Za-z_]\w*(?:\.\w+)*\s*(?:\+\+|--)\s*;?|"
    r"(?:self\.)?[A-Za-z_]\w*(?:\.\w+)*\s*\([^)]*\)\s*;?)\s*$",
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

_SUPPORTING_CONTEXT_PATTERNS: tuple[tuple[SupportingMaterialType, re.Pattern[str]], ...] = (
    (
        SupportingMaterialType.CODE_BLOCK,
        re.compile(
            r"(?:use|using|based\s+on|according\s+to|refer\s+to|complete)\s+"
            r"(?:the\s+)?(?:following|below|shown)?\s*"
            r"(?:database\s+)?(?:schema|code|listing|sql\s+schema)|"
            r"(?:المخطط\s+القاعدي|المخطط\s+التالي|الشفرة\s+التالية|الكود\s+التالي)",
            re.IGNORECASE,
        ),
    ),
    (
        SupportingMaterialType.TABLE,
        re.compile(
            r"(?:use|using|based\s+on|according\s+to|refer\s+to|complete)\s+"
            r"(?:the\s+)?(?:following|below|shown)?\s*(?:table|grid)|"
            r"(?:الجدول\s+(?:التالي|أدناه|الموضح)|استنادا\s+إلى\s+الجدول)",
            re.IGNORECASE,
        ),
    ),
    (
        SupportingMaterialType.FIGURE,
        re.compile(
            r"(?:use|using|based\s+on|according\s+to|refer\s+to|complete|study)\s+"
            r"(?:the\s+)?(?:following|below|shown)?\s*"
            r"(?:figure|diagram|uml|chart|network|topology)|"
            r"(?:(?:الشكل|المخطط|الرسم)\s+(?:التالي|أدناه|الموضح)|"
            r"استنادا\s+إلى\s+(?:الشكل|المخطط|الرسم))",
            re.IGNORECASE,
        ),
    ),
)
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
    # A ruled two-dimensional region is meaningful even when most or every
    # cell is intentionally empty: answer grids, matching banks, UML label
    # boxes, and short-answer spaces are common exam structures.  pdfplumber
    # has already required a real table geometry before this point.
    return row_count >= 2 and column_count >= 2


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
        cells: list[ExtractedTableCell] = []
        table_rows = list(table.rows)
        for row_index, row in enumerate(rows):
            row_object = table_rows[row_index] if row_index < len(table_rows) else None
            for column_index, cell_text in enumerate(row):
                cell_bbox = (
                    row_object.cells[column_index]
                    if row_object is not None and column_index < len(row_object.cells)
                    else None
                )
                cell_geometry = (
                    Geometry(
                        x0=float(cell_bbox[0]),
                        top=float(cell_bbox[1]),
                        x1=float(cell_bbox[2]),
                        bottom=float(cell_bbox[3]),
                    )
                    if cell_bbox is not None
                    else None
                )
                source_line_ids: tuple[str, ...] = ()
                logical_cell_text = (cell_text or "").strip()
                if cell_geometry is not None:
                    matched_lines = [
                        (line_index, line)
                        for line_index, line in enumerate(lines, start=1)
                        if (line_geometry := _line_geometry(page, line)) is not None
                        and cell_geometry.x0
                        <= (line_geometry.x0 + line_geometry.x1) / 2
                        <= cell_geometry.x1
                        and cell_geometry.top
                        <= (line_geometry.top + line_geometry.bottom) / 2
                        <= cell_geometry.bottom
                    ]
                    source_line_ids = tuple(
                        f"P{page_number}-N{line_index}" for line_index, _ in matched_lines
                    )
                    # ``table.extract`` can return Arabic in visual PDF order.
                    # When the geometry-aware source lines identify the cell,
                    # reconstruct its logical text from those same source spans.
                    # This keeps English tables unchanged and fixes Arabic/mixed
                    # True/False rows without OCR or translation.
                    logical_parts = [
                        _line_text(line).strip()
                        for _, line in matched_lines
                        if _line_text(line).strip()
                    ]
                    if logical_parts:
                        logical_cell_text = "\n".join(logical_parts)
                cells.append(
                    ExtractedTableCell(
                        row_index=row_index,
                        column_index=column_index,
                        original_text=logical_cell_text,
                        page_number=page_number,
                        geometry=cell_geometry,
                        confidence=0.95 if cell_bbox is not None else 0.6,
                        source_line_ids=source_line_ids,
                    )
                )
        cell_text_by_position = {
            (cell.row_index, cell.column_index): cell.original_text for cell in cells
        }
        source_text = "\n".join(
            " | ".join(
                cell_text_by_position.get((row_index, column_index), (cell or "").strip())
                for column_index, cell in enumerate(row)
            )
            for row_index, row in enumerate(rows)
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
                cells=tuple(cells),
            )
        )

    # Build code materials from contiguous runs instead of unioning every
    # code-looking line on the page.  Natural-language prompts can legitimately
    # contain code literals such as ``dequeue()`` or ``add_student()``; treating
    # one such continuation line as part of an earlier code block creates a huge
    # false material band and can make the question extractor drop that line.
    code_groups: list[list[str | PdfLayoutLine]] = []
    current_code_group: list[str | PdfLayoutLine] = []
    for line in lines:
        if is_code_line(_line_text(line)):
            current_code_group.append(line)
            continue
        if current_code_group:
            code_groups.append(current_code_group)
            current_code_group = []
    if current_code_group:
        code_groups.append(current_code_group)

    emitted_code_index = 0
    for code_lines in code_groups:
        is_fenced = any(
            _line_text(line).strip().startswith("```") for line in code_lines
        )
        if len(code_lines) < 2 and not is_fenced:
            continue
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
                local_key=f"p{page_number}:code:{emitted_code_index}",
                material_type=SupportingMaterialType.CODE_BLOCK,
                page_number=page_number,
                source_text="\n".join(_line_source_text(line) for line in code_lines),
                confidence=0.9 if code_geometry is not None else 0.65,
                geometry=code_geometry,
                extraction_method=extraction_method,
            )
        )
        emitted_code_index += 1

    # Some exam generators draw diagrams entirely with vector rectangles/lines
    # rather than embedding an image.  When an explicit Figure/شكل label sits
    # inside (or immediately below) a substantial vector rectangle, preserve
    # that rectangle as a figure material.  This prevents node labels from being
    # flattened into the surrounding question stem while remaining conservative:
    # no explicit figure label means no synthetic figure material.
    vector_objects = [*page.rects, *page.lines, *page.curves]
    for line_index, line in enumerate(lines, start=1):
        reading_text = _line_text(line)
        source_text = _line_source_text(line)
        label_match = _LABEL.match(source_text) or _LABEL.match(reading_text)
        if (
            label_match is None
            or _kind(label_match.group("kind")) is not SupportingMaterialType.FIGURE
        ):
            continue
        label_geometry = _line_geometry(page, line)
        if label_geometry is None:
            continue
        existing_nearby = [
            item
            for item in materials
            if item.material_type is SupportingMaterialType.FIGURE
            and item.geometry is not None
            and _vertical_distance(label_geometry, item.geometry) is not None
            and _vertical_distance(label_geometry, item.geometry) <= 24
        ]
        if existing_nearby:
            continue
        rectangles = []
        for item in page.rects:
            x0 = float(item.get("x0", 0.0))
            top = float(item.get("top", 0.0))
            x1 = float(item.get("x1", x0))
            bottom = float(item.get("bottom", top))
            width = x1 - x0
            height = bottom - top
            if width < 80 or height < 40:
                continue
            horizontally_contains = x0 - 8 <= (label_geometry.x0 + label_geometry.x1) / 2 <= x1 + 8
            vertically_near = top - 12 <= label_geometry.top <= bottom + 24
            if horizontally_contains and vertically_near:
                rectangles.append((width * height, Geometry(x0, top, x1, bottom)))
        if not rectangles:
            continue
        _, figure_geometry = max(rectangles, key=lambda value: value[0])
        # Require a real cluster of drawing primitives inside the candidate box.
        contained_primitives = 0
        for item in vector_objects:
            x0 = float(item.get("x0", 0.0))
            top = float(item.get("top", 0.0))
            x1 = float(item.get("x1", x0))
            bottom = float(item.get("bottom", top))
            center_x = (x0 + x1) / 2
            center_y = (top + bottom) / 2
            if (
                figure_geometry.x0 <= center_x <= figure_geometry.x1
                and figure_geometry.top <= center_y <= figure_geometry.bottom
            ):
                contained_primitives += 1
        if contained_primitives < 3:
            continue
        materials.append(
            ExtractedSupportingMaterial(
                local_key=f"p{page_number}:figure:vector:{line_index}",
                material_type=SupportingMaterialType.FIGURE,
                page_number=page_number,
                source_text=reading_text,
                confidence=0.9,
                geometry=figure_geometry,
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



def _geometry_center(value: Geometry | None) -> tuple[float, float] | None:
    if value is None:
        return None
    return ((value.x0 + value.x1) / 2, (value.top + value.bottom) / 2)


def _geometry_distance(left: Geometry | None, right: Geometry | None) -> float | None:
    left_center = _geometry_center(left)
    right_center = _geometry_center(right)
    if left_center is None or right_center is None:
        return None
    distance = (
        (left_center[0] - right_center[0]) ** 2
        + (left_center[1] - right_center[1]) ** 2
    ) ** 0.5
    return float(distance)


def _context_material_types(question_text: str) -> set[SupportingMaterialType]:
    return {
        material_type
        for material_type, pattern in _SUPPORTING_CONTEXT_PATTERNS
        if pattern.search(question_text) is not None
    }


def retain_question_linked_materials(
    *,
    questions: Sequence[Any],
    materials: Sequence[ExtractedSupportingMaterial],
    annotations: Sequence[ExtractedSupportingAnnotation],
    references: Sequence[ExtractedDocumentReference],
) -> tuple[
    list[ExtractedSupportingMaterial],
    list[ExtractedSupportingAnnotation],
]:
    """Keep only supporting context that a question actually calls for.

    Generic page tables, answer grids, cover metadata, logos, and decorative
    assets are intentionally excluded from the controlled-pilot review. A
    material survives only when an explicit label resolves to it or when a
    question contains a clear source phrase such as ``Use the following
    schema`` and there is one unambiguous physical candidate of the expected
    type on that page. The material is linked to that question for human
    confirmation; proximity alone never creates a scored exact-label claim.
    """

    material_by_key = {item.local_key: item for item in materials}
    annotations_by_label: dict[str, list[ExtractedSupportingAnnotation]] = {}
    for annotation in annotations:
        if annotation.normalized_label:
            annotations_by_label.setdefault(annotation.normalized_label, []).append(annotation)

    keep_keys: set[str] = set()
    owner_by_key: dict[str, tuple[str | None, str | None]] = {}

    # First preserve exact labeled material references (Table 1, Figure 2, ...).
    for reference in references:
        if reference.target_type is ReferenceTargetType.QUESTION:
            continue
        for annotation in annotations_by_label.get(reference.normalized_target_label, []):
            material_key = annotation.material_local_key
            if material_key is None or material_key not in material_by_key:
                continue
            material = material_by_key[material_key]
            if material.material_type.value != reference.target_type.value:
                continue
            keep_keys.add(material_key)
            owner_by_key.setdefault(
                material_key,
                (reference.question_number_label, reference.question_local_key),
            )

    # Then allow one strongly cued, unlabeled material per question/type.
    for question in questions:
        expected_types = _context_material_types(getattr(question, "text", ""))
        for material_type in expected_types:
            candidates = [
                item
                for item in materials
                if item.material_type is material_type
                and item.page_number == getattr(question, "page_number", None)
            ]
            if not candidates:
                continue
            selected: ExtractedSupportingMaterial | None = None
            if len(candidates) == 1:
                selected = candidates[0]
            else:
                ranked = sorted(
                    (
                        (distance, item)
                        for item in candidates
                        if (
                            distance := _geometry_distance(
                                getattr(question, "geometry", None), item.geometry
                            )
                        )
                        is not None
                    ),
                    key=lambda pair: pair[0],
                )
                # Multiple candidates are retained only when one is clearly nearer.
                if ranked and (len(ranked) == 1 or ranked[0][0] + 24 < ranked[1][0]):
                    selected = ranked[0][1]
            if selected is None:
                continue
            keep_keys.add(selected.local_key)
            owner_by_key.setdefault(
                selected.local_key,
                (
                    getattr(question, "number_label", None),
                    getattr(question, "local_key", None),
                ),
            )

    retained_materials: list[ExtractedSupportingMaterial] = []
    for material in materials:
        if material.local_key not in keep_keys:
            continue
        question_number_label, question_local_key = owner_by_key.get(
            material.local_key, (None, None)
        )
        retained_materials.append(
            replace(
                material,
                question_number_label=question_number_label,
                question_local_key=question_local_key,
            )
        )

    retained_annotations = [
        annotation
        for annotation in annotations
        if annotation.material_local_key in keep_keys
    ]
    return retained_materials, retained_annotations


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
    generic_patterns = (
        (ReferenceTargetType.FIGURE, SupportingMaterialType.FIGURE),
        (ReferenceTargetType.TABLE, SupportingMaterialType.TABLE),
        (ReferenceTargetType.CODE_BLOCK, SupportingMaterialType.CODE_BLOCK),
    )
    # Generic nouns such as "table" / "جدول" often describe the task itself
    # rather than point to supporting material. Create an unlabeled reference
    # only when the question contains a stronger source-context phrase already
    # trusted by the material-retention policy ("table below", "المخطط أدناه",
    # "use the following code", ...).
    for generic_type, material_type in generic_patterns:
        if any(reference.target_type is generic_type for reference in references):
            continue
        context_match = next(
            (
                pattern.search(text)
                for candidate_type, pattern in _SUPPORTING_CONTEXT_PATTERNS
                if candidate_type is material_type
            ),
            None,
        )
        if context_match is None:
            continue
        phrase = context_match.group(0).strip()
        references.append(
            ExtractedDocumentReference(
                local_key=f"{question_number_label}:generic-{generic_type.value}-ref:0",
                target_type=generic_type,
                original_text=phrase,
                target_label=phrase,
                normalized_target_label=f"{generic_type.value}:unlabeled",
                page_number=page_number,
                confidence=min(confidence, 0.85),
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
