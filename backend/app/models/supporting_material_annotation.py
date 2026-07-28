from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import SupportingAnnotationType, UploadedFileType, enum_values
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.supporting_material import SupportingMaterial


class SupportingMaterialAnnotation(Base):
    """Immutable caption or label with both original and matching-only wording."""

    __tablename__ = "supporting_material_annotations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("supporting_materials.id", ondelete="CASCADE"),
        index=True,
    )
    source_document: Mapped[UploadedFileType] = mapped_column(
        Enum(
            UploadedFileType,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        )
    )
    annotation_type: Mapped[SupportingAnnotationType] = mapped_column(
        Enum(
            SupportingAnnotationType,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        )
    )
    original_text: Mapped[str] = mapped_column(Text)
    normalized_label: Mapped[str | None] = mapped_column(String(100), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    confidence: Mapped[float] = mapped_column(Float)
    extraction_method: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="supporting_material_annotations")
    material: Mapped[SupportingMaterial | None] = relationship(back_populates="annotations")
