from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import ExtractionWarningSeverity, enum_values
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class ExtractionWarning(Base):
    __tablename__ = "extraction_warnings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[ExtractionWarningSeverity] = mapped_column(
        Enum(
            ExtractionWarningSeverity,
            native_enum=False,
            validate_strings=True,
            values_callable=enum_values,
        )
    )
    page_number: Mapped[int | None] = mapped_column(Integer, default=None)
    source_line_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    message: Mapped[str] = mapped_column(Text)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="extraction_warnings")
