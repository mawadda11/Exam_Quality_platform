"""Writes generated report PDFs to disk under the configured report root.
Reuses resolve_storage_path's path-traversal safety check, but has none of
services/storage/files.py's upload-specific concerns (streaming, declared
MIME/magic-byte validation) - report bytes are server-generated output, not
client-supplied input.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from app.services.storage.keys import generate_report_storage_key, resolve_storage_path


@dataclass(frozen=True)
class StoredReport:
    storage_key: str
    size_bytes: int
    sha256_hash: str


def store_report_pdf(
    *, content: bytes, analysis_id: uuid.UUID, report_id: uuid.UUID, report_root: str
) -> StoredReport:
    storage_key = generate_report_storage_key(analysis_id, report_id)
    path = resolve_storage_path(report_root, storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return StoredReport(
        storage_key=storage_key,
        size_bytes=len(content),
        sha256_hash=hashlib.sha256(content).hexdigest(),
    )
