from __future__ import annotations

import hashlib
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.domain import UploadedFileType
from app.services.storage.keys import generate_storage_key, resolve_storage_path
from app.services.storage.validation import (
    EOF_SEARCH_WINDOW,
    validate_declared_mime_type,
    validate_filename_extension,
    validate_magic_bytes,
    validate_pdf_trailer,
)

CHUNK_SIZE = 1024 * 1024  # 1 MiB - bounds peak memory regardless of upload size


class UploadTooLargeError(ValueError):
    """Raised when a streamed upload exceeds the configured maximum size."""


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    size_bytes: int
    sha256_hash: str


async def stream_validate_and_store(
    *,
    upload: UploadFile,
    analysis_id: uuid.UUID,
    file_type: UploadedFileType,
    upload_root: str,
    max_size_bytes: int,
) -> StoredFile:
    validate_filename_extension(upload.filename or "")
    validate_declared_mime_type(upload.content_type or "")

    Path(upload_root).mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(dir=upload_root, delete=False)
    tmp_path = Path(tmp.name)
    digest = hashlib.sha256()
    total_bytes = 0
    first_chunk_checked = False

    try:
        # Read in bounded chunks and check the running total *before* buffering more -
        # never call read() with no size, which would fully spool an oversized/
        # malicious payload before any check could reject it.
        try:
            while chunk := await upload.read(CHUNK_SIZE):
                if not first_chunk_checked:
                    validate_magic_bytes(chunk)
                    first_chunk_checked = True
                total_bytes += len(chunk)
                if total_bytes > max_size_bytes:
                    raise UploadTooLargeError(
                        f"Upload exceeds the maximum allowed size of {max_size_bytes} bytes."
                    )
                digest.update(chunk)
                tmp.write(chunk)
            if not first_chunk_checked:
                validate_magic_bytes(b"")
        finally:
            # Close the handle before any further read/move - on Windows, moving or
            # reopening a file that's still open under another handle can fail.
            tmp.close()

        tail_size = min(total_bytes, EOF_SEARCH_WINDOW)
        with tmp_path.open("rb") as handle:
            handle.seek(total_bytes - tail_size)
            validate_pdf_trailer(handle.read(tail_size))

        storage_key = generate_storage_key(analysis_id, file_type)
        final_path = resolve_storage_path(upload_root, storage_key)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_path), str(final_path))
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return StoredFile(
        storage_key=storage_key, size_bytes=total_bytes, sha256_hash=digest.hexdigest()
    )
