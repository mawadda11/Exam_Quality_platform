from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import (
    ReferenceResolutionStatus,
    ReferenceTargetType,
    UploadedFileType,
    enum_values,
)
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.question import Question
    from app.models.reference_association import ReferenceAssociation


class DocumentReference(Base):
    """Immutable explicit source reference to a material or question label."""

    __tablename__ = "document_references"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), index=True
    )
    source_document: Mapped[UploadedFileType] = mapped_column(
        Enum(
            UploadedFileType,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        )
    )
    target_type: Mapped[ReferenceTargetType] = mapped_column(
        Enum(
            ReferenceTargetType,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        )
    )
    original_text: Mapped[str] = mapped_column(Text)
    target_label: Mapped[str] = mapped_column(String(100))
    normalized_target_label: Mapped[str] = mapped_column(String(100), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    confidence: Mapped[float] = mapped_column(Float)
    extraction_method: Mapped[str] = mapped_column(String(20))
    machine_resolution_status: Mapped[ReferenceResolutionStatus] = mapped_column(
        Enum(
            ReferenceResolutionStatus,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        ),
        default=ReferenceResolutionStatus.UNRESOLVED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="document_references")
    question: Mapped[Question | None] = relationship()
    association_candidates: Mapped[list[ReferenceAssociation]] = relationship(
        back_populates="reference", cascade="all, delete-orphan"
    )
