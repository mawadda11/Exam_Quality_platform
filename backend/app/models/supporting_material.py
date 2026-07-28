from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import SupportingMaterialType, UploadedFileType, enum_values
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.question import Question
    from app.models.reference_association import ReferenceAssociation
    from app.models.supporting_material_annotation import SupportingMaterialAnnotation


class SupportingMaterial(Base):
    """Immutable machine-extracted figure, table, or code-block source record."""

    __tablename__ = "supporting_materials"

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
    material_type: Mapped[SupportingMaterialType] = mapped_column(
        Enum(
            SupportingMaterialType,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        ),
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer)
    source_text: Mapped[str] = mapped_column(Text)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    confidence: Mapped[float] = mapped_column(Float)
    extraction_method: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="supporting_materials")
    question: Mapped[Question | None] = relationship()
    annotations: Mapped[list[SupportingMaterialAnnotation]] = relationship(
        back_populates="material", cascade="all, delete-orphan"
    )
    association_candidates: Mapped[list[ReferenceAssociation]] = relationship(
        back_populates="target_material",
        foreign_keys="ReferenceAssociation.target_material_id",
    )
