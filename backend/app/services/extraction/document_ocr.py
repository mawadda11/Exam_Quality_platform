"""Provider-neutral full-document OCR boundary.

Only the normalized dataclasses in this module cross the adapter boundary.
Tesseract is the sole supported implementation today; a future engine can be
added by implementing ``DocumentOcrProvider`` and extending the factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import pdfplumber
import pytesseract

from app.services.extraction.language_detection import detect_text_language
from app.services.extraction.ocr import OCR_RESOLUTION_DPI, OcrEngine, TesseractOcrEngine
from app.services.extraction.types import Geometry

if TYPE_CHECKING:
    from app.core.config import Settings


class DocumentOcrProviderError(RuntimeError):
    """Sanitized provider failure; never include document text or private paths."""


@dataclass(frozen=True)
class NormalizedOcrToken:
    token_id: str
    original_text: str
    geometry: Geometry | None
    confidence: float | None


@dataclass(frozen=True)
class NormalizedOcrLine:
    line_id: str
    page_number: int
    reading_order: int
    original_text: str
    geometry: Geometry | None
    confidence: float | None
    language: str | None
    tokens: tuple[NormalizedOcrToken, ...] = ()


@dataclass(frozen=True)
class NormalizedOcrPage:
    page_number: int
    width: float
    height: float
    lines: tuple[NormalizedOcrLine, ...]
    language: str | None
    average_confidence: float | None
    quality_warnings: tuple[str, ...] = ()
    review_recommended: bool = False


@dataclass(frozen=True)
class NormalizedOcrDocument:
    provider_name: str
    provider_version: str | None
    extraction_method: str
    pages: tuple[NormalizedOcrPage, ...]
    warnings: tuple[str, ...] = ()
    review_recommended: bool = False


class DocumentOcrProvider(Protocol):
    provider_name: str

    def extract(self, pdf_path: Path) -> NormalizedOcrDocument: ...


class TesseractDocumentOcrProvider:
    provider_name = "tesseract"
    # Tesseract is the local fallback for unreadable pages and targeted regions.
    # Running it over every already-readable digital page creates duplicate and
    # reading-order noise without adding trustworthy evidence.
    compare_usable_native_pages = False

    def __init__(self, engine: OcrEngine | None = None) -> None:
        self._engine = engine or TesseractOcrEngine()

    def extract(self, pdf_path: Path) -> NormalizedOcrDocument:
        try:
            version = str(pytesseract.get_tesseract_version()).splitlines()[0]
        except Exception:
            version = None

        pages: list[NormalizedOcrPage] = []
        try:
            with pdfplumber.open(pdf_path) as document:
                for page_index, page in enumerate(document.pages):
                    page_number = page_index + 1
                    scale = OCR_RESOLUTION_DPI / 72.0
                    image = page.to_image(resolution=OCR_RESOLUTION_DPI).original
                    ocr_lines = self._engine.lines_for_image(image, scale)
                    normalized_lines: list[NormalizedOcrLine] = []
                    for line_index, line in enumerate(ocr_lines, start=1):
                        line_id = f"P{page_number}-L{line_index}"
                        tokens = tuple(
                            NormalizedOcrToken(
                                token_id=f"{line_id}-T{token_index}",
                                original_text=token.text,
                                geometry=token.geometry,
                                confidence=token.confidence,
                            )
                            for token_index, token in enumerate(line.tokens, start=1)
                        )
                        detected = detect_text_language(line.text)
                        normalized_lines.append(
                            NormalizedOcrLine(
                                line_id=line_id,
                                page_number=page_number,
                                reading_order=line_index,
                                original_text=line.text,
                                geometry=line.geometry,
                                confidence=line.confidence,
                                language=detected.language.value,
                                tokens=tokens,
                            )
                        )
                    confidence_values = [
                        line.confidence for line in normalized_lines if line.confidence is not None
                    ]
                    average = (
                        round(sum(confidence_values) / len(confidence_values), 4)
                        if confidence_values
                        else None
                    )
                    page_text = "\n".join(line.original_text for line in normalized_lines)
                    language = detect_text_language(page_text).language.value if page_text else None
                    pages.append(
                        NormalizedOcrPage(
                            page_number=page_number,
                            width=float(page.width),
                            height=float(page.height),
                            lines=tuple(normalized_lines),
                            language=language,
                            average_confidence=average,
                            quality_warnings=(() if normalized_lines else ("NO_OCR_TEXT",)),
                            review_recommended=average is None or average < 0.75,
                        )
                    )
        except Exception as exc:
            raise DocumentOcrProviderError("The configured document OCR provider failed.") from exc

        return NormalizedOcrDocument(
            provider_name=self.provider_name,
            provider_version=version,
            extraction_method="ocr",
            pages=tuple(pages),
            review_recommended=any(page.review_recommended for page in pages),
        )


class FakeDocumentOcrProvider:
    provider_name = "fake"
    compare_usable_native_pages = True

    def __init__(self, result: NormalizedOcrDocument) -> None:
        self.result = result
        self.calls = 0

    def extract(self, pdf_path: Path) -> NormalizedOcrDocument:
        self.calls += 1
        return self.result


def create_document_ocr_provider(settings: Settings) -> DocumentOcrProvider:
    provider = settings.exam_ocr_provider.strip().casefold()
    if provider == "tesseract":
        return TesseractDocumentOcrProvider()
    raise ValueError(f"Unsupported EXAM_OCR_PROVIDER: {settings.exam_ocr_provider}")
