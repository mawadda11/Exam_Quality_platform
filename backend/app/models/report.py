from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import ReportFormat, enum_values
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class Report(Base):
    """One immutable row per generated report artifact (M10: on-demand only,
    never generated automatically by the processing pipeline). Regenerating
    a report for the same analysis creates a new row rather than replacing
    an existing one (AI_GOVERNANCE.md #14: preserve prior generated results
    in audit history) - so an analysis may have zero, one, or many reports.

    score/label/denominator/status counts are captured here, not on
    `analyses`, because they are specifically a snapshot of what *this*
    generated PDF said at the moment it was generated - the analysis's own
    live score remains available, unchanged, via GET /analyses/{id}/score
    (M9, still computed read-time from the same, immutable Findings)."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    format: Mapped[ReportFormat] = mapped_column(
        Enum(ReportFormat, native_enum=False, validate_strings=True, values_callable=enum_values),
        default=ReportFormat.PDF,
    )
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256_hash: Mapped[str] = mapped_column(String(64))
    kb_version: Mapped[str] = mapped_column(String(50))
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    score_label: Mapped[str | None] = mapped_column(String(50), default=None)
    denominator: Mapped[int] = mapped_column(Integer)
    satisfied_count: Mapped[int] = mapped_column(Integer)
    partially_satisfied_count: Mapped[int] = mapped_column(Integer)
    not_satisfied_count: Mapped[int] = mapped_column(Integer)
    not_verified_count: Mapped[int] = mapped_column(Integer)
    not_applicable_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="reports")
