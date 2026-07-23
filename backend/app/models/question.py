from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class Question(Base):
    """Immutable once extracted (no updated_at) - matches UploadedFile's and
    ProcessingEvent's immutable-row pattern. parent_question_id is
    self-referential: a sub-question ("(a)") points at its top-level
    question ("Q1"); a top-level question has parent_question_id = None."""

    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    parent_question_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        default=None,
        index=True,
    )
    number_label: Mapped[str] = mapped_column(String(50))
    question_text: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int] = mapped_column(Integer)
    marks: Mapped[float | None] = mapped_column(Float, default=None)
    sequence: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="questions")
