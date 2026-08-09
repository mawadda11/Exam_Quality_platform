"""Deterministic native-PDF/OCR reconciliation.

The service reports disagreements; it never silently rewrites either source.
Canonical parsing continues from source lines selected by the extractor and
critical warnings remain visible until the faculty review resolves them.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.core.domain import ExtractionWarningSeverity
from app.services.extraction.document_ocr import NormalizedOcrDocument, NormalizedOcrLine
from app.services.extraction.line_classification import LineKind, classify_line
from app.services.extraction.types import (
    ExtractedSourceLine,
    ExtractionReconciliationWarning,
    Geometry,
)

_OPTION = re.compile(r"^\s*([A-Da-d]|[أبجد])\s*[).:-]\s*(.+)$")
_TECHNICAL = re.compile(
    r"(?:\b\d{1,3}(?:\.\d{1,3}){3}\b|\b[A-Z]{2,}\d*\b|[=<>^{}\\/]|0x[0-9a-f]+)",
    re.IGNORECASE,
)
_DUPLICATE_SPACE = re.compile(r"\s+")


def _normalized(text: str) -> str:
    return _DUPLICATE_SPACE.sub(" ", text).strip().casefold()


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalized(left), _normalized(right)).ratio()


def _union(left: Geometry | None, right: Geometry | None) -> Geometry | None:
    if left is None:
        return right
    if right is None:
        return left
    return Geometry(
        x0=min(left.x0, right.x0),
        top=min(left.top, right.top),
        x1=max(left.x1, right.x1),
        bottom=max(left.bottom, right.bottom),
    )


def collapse_reconciliation_warnings(
    warnings: list[ExtractionReconciliationWarning]
    | tuple[ExtractionReconciliationWarning, ...],
) -> list[ExtractionReconciliationWarning]:
    """Collapse repeated diagnostics into one review item per page/code/severity.

    OCR providers often emit several line-level diagnostics for one visual region.
    Persisting every line as a separate faculty action creates an unusable review
    screen and can require dozens of identical checkboxes.  This function keeps
    complete provenance by merging source-line IDs and geometry while presenting
    one actionable warning group.
    """

    grouped: dict[
        tuple[str, ExtractionWarningSeverity, int | None, bool],
        list[ExtractionReconciliationWarning],
    ] = {}
    for warning in warnings:
        grouped.setdefault(
            (warning.code, warning.severity, warning.page_number, warning.resolved),
            [],
        ).append(warning)

    collapsed: list[ExtractionReconciliationWarning] = []
    for (_, _, _, _), items in grouped.items():
        first = items[0]
        source_line_ids = tuple(
            dict.fromkeys(
                source_line_id
                for item in items
                for source_line_id in item.source_line_ids
            )
        )
        geometry: Geometry | None = None
        for item in items:
            geometry = _union(geometry, item.geometry)
        message = first.message
        if len(items) > 1:
            message = f"{message} ({len(items)} related occurrences on this page.)"
        collapsed.append(
            ExtractionReconciliationWarning(
                code=first.code,
                severity=first.severity,
                message=message,
                page_number=first.page_number,
                source_line_ids=source_line_ids,
                geometry=geometry,
                resolved=first.resolved,
            )
        )

    severity_order = {
        ExtractionWarningSeverity.CRITICAL: 0,
        ExtractionWarningSeverity.WARNING: 1,
        ExtractionWarningSeverity.INFO: 2,
    }
    return sorted(
        collapsed,
        key=lambda item: (
            severity_order[item.severity],
            item.page_number if item.page_number is not None else -1,
            item.code,
        ),
    )


def _is_structural(text: str) -> bool:
    classified = classify_line(text, None)
    return classified.kind in {
        LineKind.QUESTION,
        LineKind.SUBQUESTION,
        LineKind.TOTAL_MARKS,
    } or bool(_OPTION.match(text) or _TECHNICAL.search(text))


def _best_match(
    native: ExtractedSourceLine,
    candidates: list[NormalizedOcrLine],
    used: set[str],
) -> NormalizedOcrLine | None:
    available = [item for item in candidates if item.line_id not in used]
    if not available:
        return None

    def score(item: NormalizedOcrLine) -> tuple[float, float]:
        similarity = _similarity(native.original_text, item.original_text)
        distance: float
        if native.geometry is None or item.geometry is None:
            distance = abs(native.reading_order - item.reading_order)
        else:
            distance = abs(native.geometry.top - item.geometry.top) / 100.0
        return similarity - min(distance, 1.0) * 0.12, similarity

    matched = max(available, key=score)
    return matched if score(matched)[0] >= 0.25 else None


def reconcile_native_and_ocr(
    native_lines: list[ExtractedSourceLine],
    ocr_document: NormalizedOcrDocument,
) -> list[ExtractionReconciliationWarning]:
    warnings: list[ExtractionReconciliationWarning] = []
    native_by_page: dict[int, list[ExtractedSourceLine]] = {}
    for line in native_lines:
        native_by_page.setdefault(line.page_number, []).append(line)

    for page in ocr_document.pages:
        native_page = native_by_page.get(page.page_number, [])
        ocr_lines = list(page.lines)
        used_ocr: set[str] = set()
        matched_orders: list[int] = []

        for native in native_page:
            matched = _best_match(native, ocr_lines, used_ocr)
            if matched is None:
                critical = _is_structural(native.original_text)
                warnings.append(
                    ExtractionReconciliationWarning(
                        code="SOURCE_LINE_NOT_FOUND",
                        severity=(
                            ExtractionWarningSeverity.CRITICAL
                            if critical
                            else ExtractionWarningSeverity.WARNING
                        ),
                        message="A native PDF line was not found in the OCR evidence path.",
                        page_number=native.page_number,
                        source_line_ids=(native.source_line_id,),
                        geometry=native.geometry,
                    )
                )
                continue

            used_ocr.add(matched.line_id)
            matched_orders.append(matched.reading_order)
            similarity = _similarity(native.original_text, matched.original_text)
            source_ids = (native.source_line_id, matched.line_id)
            geometry = _union(native.geometry, matched.geometry)
            native_class = classify_line(native.original_text, None)
            ocr_class = classify_line(matched.original_text, None)

            if (
                native_class.kind in {LineKind.QUESTION, LineKind.SUBQUESTION}
                and ocr_class.kind in {LineKind.QUESTION, LineKind.SUBQUESTION}
                and native_class.number_label != ocr_class.number_label
            ):
                warnings.append(
                    ExtractionReconciliationWarning(
                        code="QUESTION_NUMBER_MISMATCH",
                        severity=ExtractionWarningSeverity.CRITICAL,
                        message="Native PDF and OCR question labels disagree.",
                        page_number=native.page_number,
                        source_line_ids=source_ids,
                        geometry=geometry,
                    )
                )
            native_marks = native_class.marks.value if native_class.marks else None
            ocr_marks = ocr_class.marks.value if ocr_class.marks else None
            if native_marks is not None and ocr_marks is not None and native_marks != ocr_marks:
                warnings.append(
                    ExtractionReconciliationWarning(
                        code="MARKS_MISMATCH",
                        severity=ExtractionWarningSeverity.CRITICAL,
                        message="Native PDF and OCR mark values disagree.",
                        page_number=native.page_number,
                        source_line_ids=source_ids,
                        geometry=geometry,
                    )
                )

            native_option = _OPTION.match(native.original_text)
            ocr_option = _OPTION.match(matched.original_text)
            if native_option and not ocr_option:
                code = "OPTION_MISSING"
                severity = ExtractionWarningSeverity.CRITICAL
            elif native_option and ocr_option and similarity < 0.92:
                code = "OPTION_TEXT_MISMATCH"
                severity = ExtractionWarningSeverity.CRITICAL
            elif similarity < 0.72 and _is_structural(native.original_text):
                code = "CRITICAL_TEXT_MISMATCH"
                severity = ExtractionWarningSeverity.CRITICAL
            elif similarity < 0.9:
                code = "TEXT_MISMATCH"
                severity = ExtractionWarningSeverity.WARNING
            else:
                code = ""
                severity = ExtractionWarningSeverity.INFO
            if code:
                warnings.append(
                    ExtractionReconciliationWarning(
                        code=code,
                        severity=severity,
                        message="Native PDF and OCR wording differ and require review.",
                        page_number=native.page_number,
                        source_line_ids=source_ids,
                        geometry=geometry,
                    )
                )

        if matched_orders != sorted(matched_orders):
            warnings.append(
                ExtractionReconciliationWarning(
                    code="READING_ORDER_MISMATCH",
                    severity=ExtractionWarningSeverity.WARNING,
                    message="Native PDF and OCR reading order differ on this page.",
                    page_number=page.page_number,
                )
            )

        for orphan in ocr_lines:
            if orphan.line_id in used_ocr:
                continue
            option = _OPTION.match(orphan.original_text)
            warnings.append(
                ExtractionReconciliationWarning(
                    code="ORPHAN_OPTION" if option else "UNASSIGNED_CONTENT",
                    severity=(
                        ExtractionWarningSeverity.CRITICAL
                        if option or _is_structural(orphan.original_text)
                        else ExtractionWarningSeverity.WARNING
                    ),
                    message=(
                        "An OCR answer-option line could not be assigned safely."
                        if option
                        else "OCR content could not be assigned safely to native PDF content."
                    ),
                    page_number=page.page_number,
                    source_line_ids=(orphan.line_id,),
                    geometry=orphan.geometry,
                )
            )

        normalized_seen: set[str] = set()
        for ocr_line in ocr_lines:
            normalized = _normalized(ocr_line.original_text)
            if normalized and normalized in normalized_seen:
                warnings.append(
                    ExtractionReconciliationWarning(
                        code="DUPLICATED_CONTENT",
                        severity=ExtractionWarningSeverity.WARNING,
                        message="OCR returned duplicated content on this page.",
                        page_number=page.page_number,
                        source_line_ids=(ocr_line.line_id,),
                        geometry=ocr_line.geometry,
                    )
                )
            normalized_seen.add(normalized)

    return warnings
