"""Layout-aware declared-total extraction with source-faithful provenance."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.services.extraction.line_classification import (
    has_declared_total_label,
    parse_declared_total,
)
from app.services.extraction.pdf_layout import PdfLayoutLine
from app.services.extraction.text_normalization import (
    normalize_arabic_for_matching,
    parse_localized_number,
)
from app.services.extraction.types import Geometry

_ISOLATED_TOTAL_VALUE = re.compile(
    r"^\s*(?:[:=\-–—]\s*)?(?P<value>\d+(?:\.\d+)?)"
    r"\s*(?:marks?|points?|درجة|درجات|علامة|علامات)?\s*$",
    re.IGNORECASE,
)
_MAX_ADJACENT_GAP = 24.0


@dataclass(frozen=True)
class DeclaredTotalCandidate:
    value: float
    reading_text: str
    source_text: str
    geometry: Geometry
    confidence: float


def _union_geometry(left: Geometry, right: Geometry) -> Geometry:
    return Geometry(
        x0=min(left.x0, right.x0),
        top=min(left.top, right.top),
        x1=max(left.x1, right.x1),
        bottom=max(left.bottom, right.bottom),
    )


def _vertical_gap(left: Geometry, right: Geometry) -> float:
    if left.bottom < right.top:
        return right.top - left.bottom
    if right.bottom < left.top:
        return left.top - right.bottom
    return 0.0


def _isolated_value(line: PdfLayoutLine) -> float | None:
    normalized = normalize_arabic_for_matching(line.reading_text)
    match = _ISOLATED_TOTAL_VALUE.match(normalized)
    return parse_localized_number(match.group("value")) if match is not None else None


def extract_layout_declared_total(
    lines: Sequence[PdfLayoutLine],
) -> DeclaredTotalCandidate | None:
    """Return one label-anchored total from reconstructed PDF reading order.

    A same-line label/value is preferred. If the PDF emits them as separate
    lines, only an isolated numeric value within a small geometry gap is
    accepted. Unrelated years, course codes, durations, page numbers, and
    question marks therefore cannot qualify without a total-marks label.
    """

    for line in lines:
        value = parse_declared_total(line.reading_text)
        if value is not None:
            return DeclaredTotalCandidate(
                value=value,
                reading_text=line.reading_text,
                source_text=line.raw_text,
                geometry=line.geometry,
                confidence=1.0,
            )

    for label_line in lines:
        if not has_declared_total_label(label_line.reading_text):
            continue
        nearby = sorted(
            (
                (_vertical_gap(label_line.geometry, value_line.geometry), value, value_line)
                for value_line in lines
                if value_line is not label_line
                and (value := _isolated_value(value_line)) is not None
            ),
            key=lambda item: (
                item[0],
                item[2].geometry.top,
                item[2].geometry.x0,
            ),
        )
        if not nearby or nearby[0][0] > _MAX_ADJACENT_GAP:
            continue
        _, value, value_line = nearby[0]
        return DeclaredTotalCandidate(
            value=value,
            reading_text=f"{label_line.reading_text} {value_line.reading_text}".strip(),
            source_text=f"{label_line.raw_text}\n{value_line.raw_text}".strip(),
            geometry=_union_geometry(label_line.geometry, value_line.geometry),
            confidence=0.9,
        )
    return None
