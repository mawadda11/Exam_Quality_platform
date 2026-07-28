"""Provider-neutral OCR adapter with governed Arabic/English Tesseract support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pytesseract
from PIL import Image

from app.services.extraction.types import Geometry

OCR_RESOLUTION_DPI = 300
_NO_CONFIDENCE = -1
_DEFAULT_LANGUAGE_ORDER = ("ara", "eng")


@dataclass(frozen=True)
class OcrLine:
    text: str
    geometry: Geometry
    confidence: float


class OcrEngine(Protocol):
    def lines_for_image(self, image: Image.Image, scale: float) -> list[OcrLine]:
        """Return recognized source lines in reading order.

        Geometry is converted from raster pixels back into PDF points using
        the supplied scale. Implementations must not fabricate missing text.
        """
        ...


def available_tesseract_languages() -> tuple[str, ...]:
    """Return installed language packs without failing application startup."""

    try:
        return tuple(str(item) for item in pytesseract.get_languages(config=""))
    except Exception:
        return ()


def resolve_tesseract_languages(
    requested: tuple[str, ...] = _DEFAULT_LANGUAGE_ORDER,
    available: tuple[str, ...] | None = None,
) -> str:
    """Choose installed packs, preferring Arabic+English for mixed documents."""

    installed = set(available if available is not None else available_tesseract_languages())
    selected = [language for language in requested if language in installed]
    if selected:
        return "+".join(selected)
    if "eng" in installed:
        return "eng"
    # Tesseract defaults to English when no lang is supplied. Returning an
    # empty string lets the adapter avoid an invalid explicit language value.
    return ""


class TesseractOcrEngine:
    """Group Tesseract word output into source-faithful lines.

    The default requests `ara+eng` when both packs are installed, supports an
    English-only developer machine without crashing, and exposes the selected
    language string for diagnostics/tests.
    """

    def __init__(self, languages: tuple[str, ...] = _DEFAULT_LANGUAGE_ORDER) -> None:
        self.languages = resolve_tesseract_languages(languages)

    def lines_for_image(self, image: Image.Image, scale: float) -> list[OcrLine]:
        kwargs: dict[str, object] = {"output_type": pytesseract.Output.DICT}
        if self.languages:
            kwargs["lang"] = self.languages
        data = pytesseract.image_to_data(image, **kwargs)

        words_by_line: dict[tuple[int, int, int], list[int]] = {}
        for i, text in enumerate(data["text"]):
            if not str(text).strip():
                continue
            line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            words_by_line.setdefault(line_key, []).append(i)

        lines: list[OcrLine] = []
        for line_key in sorted(words_by_line):
            indices = sorted(words_by_line[line_key], key=lambda i: data["word_num"][i])
            text = " ".join(str(data["text"][i]).strip() for i in indices)

            lefts = [int(data["left"][i]) for i in indices]
            tops = [int(data["top"][i]) for i in indices]
            rights = [int(data["left"][i]) + int(data["width"][i]) for i in indices]
            bottoms = [int(data["top"][i]) + int(data["height"][i]) for i in indices]
            geometry = Geometry(
                x0=min(lefts) / scale,
                top=min(tops) / scale,
                x1=max(rights) / scale,
                bottom=max(bottoms) / scale,
            )

            confidences = [
                float(data["conf"][i]) for i in indices if float(data["conf"][i]) != _NO_CONFIDENCE
            ]
            confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
            lines.append(OcrLine(text=text, geometry=geometry, confidence=confidence))

        return lines
