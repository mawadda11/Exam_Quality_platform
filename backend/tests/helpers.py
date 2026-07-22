from __future__ import annotations


def auth_header(email: str) -> dict[str, str]:
    return {"X-Dev-User-Email": email}


def pdf_bytes_of_size(total_size: int) -> bytes:
    """A minimal-but-valid-shaped PDF byte string padded to an exact total size,
    so size-boundary tests can request precise byte counts."""
    header = b"%PDF-1.4\n"
    footer = b"\n%%EOF"
    filler_len = max(total_size - len(header) - len(footer), 0)
    return header + (b"0" * filler_len) + footer


def valid_pdf_bytes() -> bytes:
    return pdf_bytes_of_size(64)


def pdf_missing_eof_bytes() -> bytes:
    return b"%PDF-1.4\n" + b"0" * 32


def non_pdf_bytes() -> bytes:
    return b"this is definitely not a pdf file"
