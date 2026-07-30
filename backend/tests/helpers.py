from __future__ import annotations

import uuid

from fpdf import FPDF

from app.core.config import Settings
from app.services.auth.tokens import create_access_token


def auth_header(email: str) -> dict[str, str]:
    normalized = email.strip().lower()
    settings = Settings(
        app_env="test",
        secret_key="test-secret-key-not-for-production",
        database_url="sqlite:///:memory:",
    )
    token, _ = create_access_token(
        user_id=uuid.uuid5(uuid.NAMESPACE_URL, normalized),
        email=normalized,
        display_name=normalized.split("@", maxsplit=1)[0],
        token_version=0,
        settings=settings,
    )
    return {"Authorization": f"Bearer {token}"}


def valid_pdf_bytes() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Valid PDF fixture")
    return bytes(pdf.output())


def pdf_bytes_of_size(total_size: int) -> bytes:
    """A parser-valid PDF padded to an exact size for upload-boundary tests."""
    content = valid_pdf_bytes()
    if total_size < len(content):
        raise ValueError(f"Requested size must be at least {len(content)} bytes.")

    marker_index = content.rfind(b"%%EOF")
    padding = b" " * (total_size - len(content))
    return content[:marker_index] + padding + content[marker_index:]


def corrupted_pdf_bytes() -> bytes:
    """Has accepted outer markers but no parseable PDF object structure."""
    return b"%PDF-1.4\nthis is not a PDF object graph\n%%EOF"


def truncated_pdf_bytes() -> bytes:
    content = valid_pdf_bytes()
    marker_index = content.rfind(b"%%EOF")
    return content[:marker_index]


def encrypted_pdf_bytes() -> bytes:
    pdf = FPDF()
    pdf.set_encryption(owner_password="fixture-owner", user_password="fixture-user")
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Password-protected PDF fixture")
    return bytes(pdf.output())


def non_pdf_bytes() -> bytes:
    return b"this is definitely not a pdf file"
