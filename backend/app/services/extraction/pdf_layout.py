"""Geometry-aware PDF reading order without mutating source spans.

Some digital PDF producers store Arabic glyphs in visual order while also
placing Latin fragments according to an RTL paragraph flow.  pdfplumber's
default text is useful audit source, but is not always suitable for matching.
This module keeps those source spans untouched and derives a second,
geometry-based reading representation solely for parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pdfplumber.page import Page

from app.services.extraction.types import Geometry

_ARABIC = re.compile(r"[\u0600-\u06ff\uFB50-\uFDFF\uFE70-\uFEFF]")
_LATIN_OR_DIGIT = re.compile(r"[A-Za-z0-9]")
_ARABIC_SINGLE_LETTER = re.compile(r"[\u0621-\u064a]")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,.;:!?،؛])")
_SPACE_AFTER_OPEN = re.compile(r"([\[(])\s+")
_SPACE_BEFORE_CLOSE = re.compile(r"\s+([\])])")
_LINE_TOLERANCE = 6.5


def _logical_rtl_token(value: str) -> str:
    """Repair paired punctuation stored as one visual-order RTL token."""

    return {
        ")(": "()",
        "][": "[]",
        "}{": "{}",
    }.get(value, value)


def _rtl_reading_tokens(words: list[dict[str, Any]]) -> list[str]:
    """Return logical token order for an RTL line with embedded LTR runs.

    PDF word geometry is physical.  Reversing the entire line correctly orders
    Arabic words, but it also reverses multi-token English/technical phrases
    such as ``REST API``, ``HTTP method``, ``Code 1`` and ``Input Validation``.
    Build the RTL base order, then restore each contiguous Latin/digit run to
    its natural left-to-right order.  Single technical tokens remain unchanged.
    """

    ordered = sorted(words, key=lambda item: float(item["x0"]), reverse=True)
    result: list[str] = []
    index = 0
    while index < len(ordered):
        text = str(ordered[index]["logical_text"])
        if (
            _ARABIC_SINGLE_LETTER.fullmatch(text) is not None
            and index + 1 < len(ordered)
            and str(ordered[index + 1]["logical_text"]) == ")("
        ):
            result.append(f"({text})")
            index += 2
            continue
        if _ARABIC.search(text) is None and _LATIN_OR_DIGIT.search(text) is not None:
            run: list[str] = []
            while index < len(ordered):
                candidate = str(ordered[index]["logical_text"])
                if (
                    _ARABIC.search(candidate) is not None
                    or _LATIN_OR_DIGIT.search(candidate) is None
                ):
                    break
                run.append(candidate)
                index += 1
            result.extend(reversed(run))
            continue
        result.append(_logical_rtl_token(text))
        index += 1
    return result


@dataclass(frozen=True)
class PdfLayoutToken:
    original_text: str
    geometry: Geometry


@dataclass(frozen=True)
class PdfLayoutLine:
    raw_text: str
    reading_text: str
    page_number: int
    geometry: Geometry
    source_spans: tuple[str, ...]
    tokens: tuple[PdfLayoutToken, ...] = ()


def _bbox_key(word: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        round(float(word["x0"]), 2),
        round(float(word["top"]), 2),
        round(float(word["x1"]), 2),
        round(float(word["bottom"]), 2),
    )


def _geometry(words: list[dict[str, Any]]) -> Geometry:
    return Geometry(
        x0=min(float(word["x0"]) for word in words),
        top=min(float(word["top"]) for word in words),
        x1=max(float(word["x1"]) for word in words),
        bottom=max(float(word["bottom"]) for word in words),
    )


def _clean_join(tokens: list[str]) -> str:
    value = " ".join(token for token in tokens if token).strip()
    value = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", value)
    value = _SPACE_AFTER_OPEN.sub(r"\1", value)
    value = _SPACE_BEFORE_CLOSE.sub(r"\1", value)

    # Some Arabic PDFs expose tanween/alef glyphs as zero-width standalone
    # tokens. Reattach only the unambiguous forms instead of performing broad
    # Arabic rewriting, so the canonical text remains source-faithful.
    value = re.sub(r"\u064b\s+([\u0621-\u064a]+)\s+ا\b", r"\1ًا", value)
    value = re.sub(r"([\u0621-\u064a]\u064b)\s+ا\b", r"\1ا", value)
    value = re.sub(r"(?<!\S)[\u064c-\u0652](?!\S)", "", value)
    value = re.sub(r" {2,}", " ", value).strip()
    return value


def _inside_bbox(word: dict[str, Any], bbox: tuple[float, float, float, float]) -> bool:
    x0, top, x1, bottom = bbox
    center_x = (float(word["x0"]) + float(word["x1"])) / 2
    center_y = (float(word["top"]) + float(word["bottom"])) / 2
    return x0 <= center_x <= x1 and top <= center_y <= bottom


def extract_layout_lines(
    page: Page,
    *,
    page_number: int,
    bbox: tuple[float, float, float, float] | None = None,
) -> list[PdfLayoutLine]:
    default_words = list(page.extract_words(use_text_flow=False))
    rtl_words = list(page.extract_words(use_text_flow=False, char_dir="rtl"))
    flow_words = list(page.extract_words(use_text_flow=True))
    if bbox is not None:
        default_words = [word for word in default_words if _inside_bbox(word, bbox)]
        rtl_words = [word for word in rtl_words if _inside_bbox(word, bbox)]
        flow_words = [word for word in flow_words if _inside_bbox(word, bbox)]
    if not default_words and not rtl_words:
        return []

    default_by_bbox = {_bbox_key(word): word for word in default_words}
    merged_words: list[dict[str, Any]] = []
    for rtl_word in rtl_words:
        default_word = default_by_bbox.get(_bbox_key(rtl_word))
        rtl_text = str(rtl_word["text"])
        default_text = str(default_word["text"]) if default_word is not None else rtl_text
        logical_text = rtl_text if _ARABIC.search(rtl_text + default_text) else default_text
        merged_words.append(
            {
                **rtl_word,
                "raw_text": default_text,
                "logical_text": logical_text,
            }
        )

    groups: list[dict[str, Any]] = []
    for word in sorted(merged_words, key=lambda item: (float(item["top"]), float(item["x0"]))):
        top = float(word["top"])
        group = (
            groups[-1]
            if groups and abs(top - float(groups[-1]["mean_top"])) <= _LINE_TOLERANCE
            else None
        )
        if group is None:
            groups.append({"mean_top": top, "words": [word]})
            continue
        group["words"].append(word)
        group["mean_top"] = sum(float(item["top"]) for item in group["words"]) / len(group["words"])

    lines: list[PdfLayoutLine] = []
    for group in groups:
        words = list(group["words"])
        geometry = _geometry(words)
        physical = sorted(words, key=lambda item: float(item["x0"]))
        has_arabic = any(_ARABIC.search(str(item["logical_text"])) for item in words)
        if has_arabic:
            reading_tokens = _rtl_reading_tokens(words)
        else:
            matching_flow = [
                word
                for word in flow_words
                if float(word["bottom"]) >= geometry.top
                and float(word["top"]) <= geometry.bottom
                and float(word["x1"]) >= geometry.x0
                and float(word["x0"]) <= geometry.x1
            ]
            reading_tokens = [str(word["text"]) for word in matching_flow]
            if not reading_tokens:
                reading_tokens = [str(item["logical_text"]) for item in physical]
        source_spans = tuple(str(item["raw_text"]) for item in physical)
        tokens = tuple(
            PdfLayoutToken(
                original_text=str(item["raw_text"]),
                geometry=_geometry([item]),
            )
            for item in physical
        )
        lines.append(
            PdfLayoutLine(
                raw_text=_clean_join(list(source_spans)),
                reading_text=_clean_join(reading_tokens),
                page_number=page_number,
                geometry=geometry,
                source_spans=source_spans,
                tokens=tokens,
            )
        )
    return sorted(lines, key=lambda line: (line.geometry.top, line.geometry.x0))
