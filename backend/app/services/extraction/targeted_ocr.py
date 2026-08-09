"""Bounded local OCR recovery for visually identified missing regions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from app.services.extraction.ocr import OCR_RESOLUTION_DPI, OcrEngine, TesseractOcrEngine
from app.services.extraction.types import (
    ExtractedSourceLine,
    ExtractedSourceToken,
    Geometry,
)


@dataclass(frozen=True)
class TargetedOcrResult:
    lines: tuple[ExtractedSourceLine, ...]

    @property
    def text(self) -> str:
        return " ".join(line.original_text.strip() for line in self.lines).strip()


def _offset_geometry(value: Geometry, *, x_offset: float, y_offset: float) -> Geometry:
    return Geometry(
        x0=value.x0 + x_offset,
        top=value.top + y_offset,
        x1=value.x1 + x_offset,
        bottom=value.bottom + y_offset,
    )


def targeted_tesseract_ocr(
    pdf_path: Path,
    *,
    page_number: int,
    geometry: Geometry,
    candidate_id: str,
    engine: OcrEngine | None = None,
) -> TargetedOcrResult:
    """OCR one governed PDF-coordinate crop; never rerender unrelated pages."""

    selected_engine = engine or TesseractOcrEngine()
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "-", candidate_id)[:40] or "candidate"
    with pdfplumber.open(pdf_path) as document:
        if page_number < 1 or page_number > len(document.pages):
            return TargetedOcrResult(())
        page = document.pages[page_number - 1]
        x0 = max(0.0, min(float(page.width), geometry.x0))
        top = max(0.0, min(float(page.height), geometry.top))
        x1 = max(x0, min(float(page.width), geometry.x1))
        bottom = max(top, min(float(page.height), geometry.bottom))
        if x1 - x0 < 2 or bottom - top < 2:
            return TargetedOcrResult(())
        scale = OCR_RESOLUTION_DPI / 72.0
        image = page.to_image(resolution=OCR_RESOLUTION_DPI).original
        crop = image.crop(
            (
                round(x0 * scale),
                round(top * scale),
                round(x1 * scale),
                round(bottom * scale),
            )
        )
        ocr_lines = selected_engine.lines_for_image(crop, scale)

    lines: list[ExtractedSourceLine] = []
    for line_index, line in enumerate(ocr_lines, start=1):
        line_id = f"P{page_number}-R{safe_id}-L{line_index}"
        lines.append(
            ExtractedSourceLine(
                source_line_id=line_id,
                provider="tesseract",
                provider_version=None,
                page_number=page_number,
                reading_order=line_index,
                original_text=line.text,
                geometry=_offset_geometry(line.geometry, x_offset=x0, y_offset=top),
                confidence=line.confidence,
                extraction_method="targeted_ocr",
                tokens=tuple(
                    ExtractedSourceToken(
                        token_id=f"{line_id}-T{token_index}",
                        original_text=token.text,
                        geometry=_offset_geometry(
                            token.geometry,
                            x_offset=x0,
                            y_offset=top,
                        ),
                        confidence=token.confidence,
                    )
                    for token_index, token in enumerate(line.tokens, start=1)
                ),
                page_width=float(page.width),
                page_height=float(page.height),
            )
        )
    return TargetedOcrResult(tuple(lines))
