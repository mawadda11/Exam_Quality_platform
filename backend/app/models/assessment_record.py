from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class AssessmentRecord(Base):
    """Immutable once extracted (no updated_at) - matches Question/Evidence.
    Raw extracted TP-153 evidence only; assessment-method consistency
    evaluation against the exam is later-milestone rule-engine work."""

    __tablename__ = "assessment_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    method: Mapped[str] = mapped_column(String(200))
    activity: Mapped[str | None] = mapped_column(String(200), default=None)
    percentage: Mapped[float | None] = mapped_column(Float, default=None)
    page_number: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="assessment_records")
