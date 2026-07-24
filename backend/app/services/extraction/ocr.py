"""OCR adapter: a provider-neutral interface (per docs/ARCHITECTURE.md's "OCR/
layout adapters: provider-neutral extraction interfaces") plus one concrete,
local implementation backed by Tesseract via pytesseract.

Tesseract was chosen over a cloud OCR vendor specifically so exam content
never leaves the server - docs/SECURITY_AND_PRIVACY.md requires an
undocumented deployment privacy-policy decision before sending files to any
external provider, and no such decision exists in this repository. Tesseract
needs the `tesseract-ocr` system package installed (see backend/Dockerfile);
pytesseract is only a thin wrapper that shells out to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pytesseract
from PIL import Image

from app.services.extraction.types import Geometry

# Tesseract's own documentation recommends ~300 DPI for best accuracy.
OCR_RESOLUTION_DPI = 300

# Tesseract emits confidence -1 for structural/non-text entries (e.g. block
# or paragraph boundaries with no recognized word) - these carry no text and
# must be excluded from both line-text reconstruction and confidence
# averaging, not counted as zero-confidence words.
_NO_CONFIDENCE = -1


@dataclass(frozen=True)
class OcrLine:
    text: str
    geometry: Geometry
    confidence: float


class OcrEngine(Protocol):
    def lines_for_image(self, image: Image.Image, scale: float) -> list[OcrLine]:
        """Returns one OcrLine per recognized line of text in `image`, in
        reading order. `scale` converts the image's pixel coordinates back to
        the PDF page's point coordinate space (pixels / scale = points) -
        callers rasterize at OCR_RESOLUTION_DPI and pass scale =
        OCR_RESOLUTION_DPI / 72 (72 points per inch), so returned Geometry is
        directly comparable to a digitally-extracted page's own geometry."""
        ...


class TesseractOcrEngine:
    """Groups Tesseract's word-level output (image_to_data) back into lines
    by (block, paragraph, line) so downstream classification can work with
    whole lines exactly as it does for a digital PDF's native text."""

    def lines_for_image(self, image: Image.Image, scale: float) -> list[OcrLine]:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        words_by_line: dict[tuple[int, int, int], list[int]] = {}
        for i, text in enumerate(data["text"]):
            if not text.strip():
                continue
            line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            words_by_line.setdefault(line_key, []).append(i)

        lines: list[OcrLine] = []
        for line_key in sorted(words_by_line):
            indices = sorted(words_by_line[line_key], key=lambda i: data["word_num"][i])
            text = " ".join(data["text"][i].strip() for i in indices)

            lefts = [data["left"][i] for i in indices]
            tops = [data["top"][i] for i in indices]
            rights = [data["left"][i] + data["width"][i] for i in indices]
            bottoms = [data["top"][i] + data["height"][i] for i in indices]
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
