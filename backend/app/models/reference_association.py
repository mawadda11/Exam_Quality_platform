from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import AssociationBasis, enum_values
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.document_reference import DocumentReference
    from app.models.extraction_review_revision import ExtractionReviewRevision
    from app.models.question import Question
    from app.models.supporting_material import SupportingMaterial


class ReferenceAssociation(Base):
    """Immutable candidate link; revision_id NULL identifies machine candidates."""

    __tablename__ = "reference_associations"
    __table_args__ = (
        CheckConstraint(
            "(target_material_id IS NOT NULL AND target_question_id IS NULL) OR "
            "(target_material_id IS NULL AND target_question_id IS NOT NULL)",
            name="ck_reference_associations_one_target",
        ),
        UniqueConstraint(
            "reference_id",
            "target_material_id",
            "target_question_id",
            "review_revision_id",
            "basis",
            name="uq_reference_association_candidate_revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_references.id", ondelete="CASCADE"),
        index=True,
    )
    target_material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("supporting_materials.id", ondelete="CASCADE"),
        index=True,
    )
    target_question_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    review_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("extraction_review_revisions.id", ondelete="CASCADE"),
        index=True,
    )
    basis: Mapped[AssociationBasis] = mapped_column(
        Enum(
            AssociationBasis,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        )
    )
    confidence: Mapped[float] = mapped_column(Float)
    proximity_distance: Mapped[float | None] = mapped_column(Float, default=None)
    exact_label_match: Mapped[bool] = mapped_column(Boolean, default=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    ambiguity_reason: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    reference: Mapped[DocumentReference] = relationship(back_populates="association_candidates")
    target_material: Mapped[SupportingMaterial | None] = relationship(
        back_populates="association_candidates",
        foreign_keys=[target_material_id],
    )
    target_question: Mapped[Question | None] = relationship(foreign_keys=[target_question_id])
    review_revision: Mapped[ExtractionReviewRevision | None] = relationship()
