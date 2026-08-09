from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import QuestionReviewStatus, QuestionType, enum_values
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.question_blank import QuestionBlank
    from app.models.question_option import QuestionOption
    from app.models.question_source_span import QuestionSourceSpan


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
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(
            QuestionType,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        ),
        default=QuestionType.UNKNOWN,
    )
    instructions: Mapped[str | None] = mapped_column(Text, default=None)
    page_number: Mapped[int] = mapped_column(Integer)
    marks: Mapped[float | None] = mapped_column(Float, default=None)
    sequence: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    extraction_method: Mapped[str] = mapped_column(String(30), default="direct_text")
    review_status: Mapped[QuestionReviewStatus] = mapped_column(
        Enum(
            QuestionReviewStatus,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        ),
        default=QuestionReviewStatus.MACHINE_EXTRACTED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="questions")
    options: Mapped[list[QuestionOption]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.sequence"
    )
    blanks: Mapped[list[QuestionBlank]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionBlank.blank_index",
    )
    source_spans: Mapped[list[QuestionSourceSpan]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )
