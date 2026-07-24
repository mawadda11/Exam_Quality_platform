from __future__ import annotations

from pathlib import Path

import pdfplumber

PDF_MAGIC_BYTES = b"%PDF-"
PDF_EOF_MARKER = b"%%EOF"
EOF_SEARCH_WINDOW = 2048
ALLOWED_PDF_MIME_TYPES = frozenset({"application/pdf"})
PDF_READABILITY_ERROR = "File content could not be opened as a readable PDF."


class UploadValidationError(ValueError):
    """Raised when an uploaded file fails an extension/MIME/structural check."""


def validate_filename_extension(filename: str) -> None:
    if not filename.lower().endswith(".pdf"):
        raise UploadValidationError(f"Filename '{filename}' must end with .pdf.")


def validate_declared_mime_type(mime_type: str) -> None:
    if mime_type not in ALLOWED_PDF_MIME_TYPES:
        raise UploadValidationError(f"Content-Type '{mime_type}' is not an accepted PDF MIME type.")


def validate_magic_bytes(first_chunk: bytes) -> None:
    if not first_chunk.startswith(PDF_MAGIC_BYTES):
        raise UploadValidationError("File content does not start with the PDF signature (%PDF-).")


def validate_pdf_trailer(tail_bytes: bytes) -> None:
    """Lightweight structural sanity check before parser readability validation."""
    if PDF_EOF_MARKER not in tail_bytes:
        raise UploadValidationError("File content is missing the PDF end-of-file marker (%%EOF).")


def validate_pdf_readability(pdf_path: Path) -> None:
    """Require the existing PDF parser to open and enumerate at least one page.

    Text extraction is deliberately not required here: a valid scanned PDF
    has pages but may have no digital text layer and must remain acceptable
    for the exam extractor's OCR fallback.
    """
    try:
        with pdfplumber.open(pdf_path) as document:
            if not document.pages:
                raise UploadValidationError(PDF_READABILITY_ERROR)
    except UploadValidationError:
        raise
    except Exception as exc:
        raise UploadValidationError(PDF_READABILITY_ERROR) from exc
