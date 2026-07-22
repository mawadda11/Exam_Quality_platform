from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.core.domain import UploadedFileType
from app.services.storage.keys import generate_storage_key, resolve_storage_path
from app.services.storage.validation import (
    UploadValidationError,
    validate_declared_mime_type,
    validate_filename_extension,
    validate_magic_bytes,
    validate_pdf_trailer,
)


def test_validate_filename_extension_rejects_non_pdf() -> None:
    with pytest.raises(UploadValidationError):
        validate_filename_extension("notes.txt")


def test_validate_filename_extension_accepts_pdf_case_insensitive() -> None:
    validate_filename_extension("Exam.PDF")


def test_validate_declared_mime_type_rejects_wrong_type() -> None:
    with pytest.raises(UploadValidationError):
        validate_declared_mime_type("text/plain")


def test_validate_declared_mime_type_accepts_application_pdf() -> None:
    validate_declared_mime_type("application/pdf")


def test_validate_magic_bytes_rejects_non_pdf_header() -> None:
    with pytest.raises(UploadValidationError):
        validate_magic_bytes(b"not a pdf")


def test_validate_magic_bytes_accepts_pdf_header() -> None:
    validate_magic_bytes(b"%PDF-1.4\n...")


def test_validate_pdf_trailer_rejects_missing_eof() -> None:
    with pytest.raises(UploadValidationError):
        validate_pdf_trailer(b"...no marker here...")


def test_validate_pdf_trailer_accepts_eof_marker() -> None:
    validate_pdf_trailer(b"...content...\n%%EOF")


def test_generate_storage_key_never_contains_traversal_segments() -> None:
    analysis_id = uuid.uuid4()
    key = generate_storage_key(analysis_id, UploadedFileType.EXAM)
    assert ".." not in key
    assert key.startswith(f"{analysis_id}/exam/")
    assert key.endswith(".pdf")


def test_generate_storage_key_is_unique_across_calls() -> None:
    analysis_id = uuid.uuid4()
    keys = {generate_storage_key(analysis_id, UploadedFileType.EXAM) for _ in range(50)}
    assert len(keys) == 50


def test_resolve_storage_path_stays_within_root(tmp_path: Path) -> None:
    key = generate_storage_key(uuid.uuid4(), UploadedFileType.TP153)
    resolved = resolve_storage_path(tmp_path, key)
    assert resolved.is_relative_to(tmp_path.resolve())


def test_resolve_storage_path_rejects_escaping_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve_storage_path(tmp_path, "../../etc/passwd")
