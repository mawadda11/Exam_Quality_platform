"""Authenticated raster previews for human extraction review.

The preview is intentionally derived from the immutable uploaded PDF. It never
changes the source document and never promotes OCR or AI text to canonical
content. Geometry is expressed in PDF points (the same coordinate system used
by pdfplumber extraction records).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from app.services.extraction.types import Geometry


class PdfPreviewError(ValueError):
    """Raised when a requested page or crop cannot be rendered safely."""


@dataclass(frozen=True)
class RenderedPdfPreview:
    content: bytes
    page_width: float
    page_height: float


def _clamp_geometry(
    geometry: Geometry,
    *,
    page_width: float,
    page_height: float,
) -> Geometry:
    x0 = max(0.0, min(page_width, geometry.x0))
    top = max(0.0, min(page_height, geometry.top))
    x1 = max(x0, min(page_width, geometry.x1))
    bottom = max(top, min(page_height, geometry.bottom))
    if x1 - x0 < 1 or bottom - top < 1:
        raise PdfPreviewError("The selected PDF region is too small to render.")
    return Geometry(x0=x0, top=top, x1=x1, bottom=bottom)


@lru_cache(maxsize=24)
def _render_base_page(
    pdf_path_text: str,
    file_mtime_ns: int,
    page_number: int,
    dpi: int,
) -> tuple[bytes, float, float]:
    """Render and cache one immutable full page inside the backend process.

    The file modification timestamp is part of the key, so a replaced upload can
    never reuse a stale page image. Caching the full page also means the visual
    review and question crops do not repeatedly open and rasterize the PDF.
    """

    del file_mtime_ns  # Used only as a cache-key component.
    pdf_path = Path(pdf_path_text)
    try:
        with fitz.open(pdf_path) as document:
            if page_number > document.page_count:
                raise PdfPreviewError("The requested PDF page does not exist.")
            page = document.load_page(page_number - 1)
            page_width = float(page.rect.width)
            page_height = float(page.rect.height)
            scale = dpi / 72.0
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            content = pixmap.tobytes("png")
    except PdfPreviewError:
        raise
    except (fitz.FileDataError, fitz.EmptyFileError, OSError, ValueError) as exc:
        raise PdfPreviewError("The exam PDF page could not be rendered.") from exc
    return content, page_width, page_height


def render_pdf_page_preview(
    pdf_path: Path,
    *,
    page_number: int,
    geometry: Geometry | None = None,
    crop: bool = False,
    padding_points: float = 10.0,
    dpi: int = 120,
) -> RenderedPdfPreview:
    """Render one page, optionally highlighting or cropping one source region."""

    if dpi < 72 or dpi > 180:
        raise PdfPreviewError("PDF preview resolution is outside the supported range.")
    if page_number < 1:
        raise PdfPreviewError("PDF page numbers start at 1.")
    try:
        file_mtime_ns = pdf_path.stat().st_mtime_ns
    except OSError as exc:
        raise PdfPreviewError("The exam PDF is unavailable.") from exc

    content, page_width, page_height = _render_base_page(
        str(pdf_path.resolve()),
        file_mtime_ns,
        page_number,
        dpi,
    )
    if geometry is None:
        return RenderedPdfPreview(
            content=content,
            page_width=page_width,
            page_height=page_height,
        )

    bounded = _clamp_geometry(
        geometry,
        page_width=page_width,
        page_height=page_height,
    )
    try:
        image = Image.open(BytesIO(content)).convert("RGBA")
    except (OSError, ValueError) as exc:
        raise PdfPreviewError("The exam PDF page image could not be prepared.") from exc

    scale = dpi / 72.0
    x0 = bounded.x0
    top = bounded.top
    x1 = bounded.x1
    bottom = bounded.bottom
    if crop:
        padding = max(0.0, min(72.0, padding_points))
        x0 = max(0.0, x0 - padding)
        top = max(0.0, top - padding)
        x1 = min(page_width, x1 + padding)
        bottom = min(page_height, bottom + padding)
        image = image.crop(
            (
                round(x0 * scale),
                round(top * scale),
                round(x1 * scale),
                round(bottom * scale),
            )
        )
    else:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        width = max(3, round(dpi / 36))
        draw.rectangle(
            (
                round(x0 * scale),
                round(top * scale),
                round(x1 * scale),
                round(bottom * scale),
            ),
            fill=(20, 184, 166, 42),
            outline=(13, 148, 136, 255),
            width=width,
        )
        image = Image.alpha_composite(image, overlay)

    output = BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    return RenderedPdfPreview(
        content=output.getvalue(),
        page_width=page_width,
        page_height=page_height,
    )
