from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import UploadedFileType, enum_values
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class UploadedFile(Base):
    """Rows are immutable once created (no updated_at) - re-uploading the same
    (analysis, file_type) slot is rejected by the API, never silently replaced."""

    __tablename__ = "uploaded_files"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id", "file_type", name="uq_uploaded_files_analysis_id_file_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    file_type: Mapped[UploadedFileType] = mapped_column(
        Enum(
            UploadedFileType,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        )
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="files")
