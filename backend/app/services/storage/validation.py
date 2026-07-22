from __future__ import annotations

PDF_MAGIC_BYTES = b"%PDF-"
PDF_EOF_MARKER = b"%%EOF"
EOF_SEARCH_WINDOW = 2048
ALLOWED_PDF_MIME_TYPES = frozenset({"application/pdf"})


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
    """Lightweight structural sanity check only (catches truncated/non-PDF content) -
    not a real PDF parser. Deep malicious-PDF defense belongs to the extraction phase."""
    if PDF_EOF_MARKER not in tail_bytes:
        raise UploadValidationError("File content is missing the PDF end-of-file marker (%%EOF).")
