from __future__ import annotations

import uuid
from pathlib import Path

from app.core.domain import UploadedFileType


def generate_storage_key(analysis_id: uuid.UUID, file_type: UploadedFileType) -> str:
    """The only inputs are a server-verified analysis id and a fresh UUID - the
    client-supplied filename never influences this path, by construction."""
    return f"{analysis_id}/{file_type.value}/{uuid.uuid4().hex}.pdf"


def generate_report_storage_key(analysis_id: uuid.UUID, report_id: uuid.UUID) -> str:
    """Server-generated only (analysis id + the report's own fresh id) -
    reports are generated output, never a client-supplied filename, by
    construction. Kept separate from generate_storage_key: reports aren't an
    UploadedFileType (they're not uploads), and each regeneration produces a
    new report_id (M10 decision: never replace an existing Report row)."""
    return f"{analysis_id}/{report_id}.pdf"


def resolve_storage_path(upload_root: str | Path, storage_key: str) -> Path:
    root = Path(upload_root).resolve()
    candidate = (root / storage_key).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("Resolved storage path escapes the configured upload root.")
    return candidate
