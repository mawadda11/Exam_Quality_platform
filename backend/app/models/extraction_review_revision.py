from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class ExtractionReviewRevision(Base):
    """Immutable complete extraction snapshot.

    Revision 1 will preserve the original machine extraction in M3. Later
    revisions will be appended by M4; this model deliberately has no
    ``updated_at`` field or mutable edit-event children.
    """

    __tablename__ = "extraction_review_revisions"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "revision_number",
            name="uq_extraction_review_revisions_analysis_revision",
        ),
        CheckConstraint(
            "revision_number >= 1",
            name="ck_extraction_review_revisions_positive_revision",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE")
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(
        back_populates="review_revisions",
        foreign_keys=[analysis_id],
    )
