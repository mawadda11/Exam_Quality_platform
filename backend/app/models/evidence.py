from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import UploadedFileType, enum_values
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class Evidence(Base):
    """Immutable once extracted (no updated_at). question_id is nullable -
    exam-level evidence (e.g. general instructions) isn't tied to a single
    question. source_document reuses UploadedFileType since evidence always
    originates from one of the analysis's uploaded documents."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    source_document: Mapped[UploadedFileType] = mapped_column(
        Enum(
            UploadedFileType, native_enum=False, validate_strings=True, values_callable=enum_values
        )
    )
    evidence_type: Mapped[str] = mapped_column(String(100))
    page_number: Mapped[int] = mapped_column(Integer)
    item_reference: Mapped[str] = mapped_column(String(100))
    extracted_text: Mapped[str] = mapped_column(Text)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="evidence")
