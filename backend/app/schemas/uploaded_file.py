from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.domain import UploadedFileType


class UploadedFileResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    file_type: UploadedFileType
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256_hash: str
    created_at: datetime
