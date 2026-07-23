from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import AcademicStatus, enum_values
from app.db.base import Base
from app.db.mixins import utcnow

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.evidence import Evidence


class Finding(Base):
    """Immutable once created (no updated_at) - matches Evidence's and
    Question's immutable-row pattern. One row per rule execution; requirement_id
    and rule_id are the official knowledge-base identifiers from
    app.services.rules.identifiers, never provisional strings."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[str] = mapped_column(String(50))
    rule_id: Mapped[str] = mapped_column(String(50))
    status: Mapped[AcademicStatus] = mapped_column(
        Enum(AcademicStatus, native_enum=False, validate_strings=True, values_callable=enum_values)
    )
    explanation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    evaluator_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis: Mapped[Analysis] = relationship(back_populates="findings")
    evidence_links: Mapped[list[FindingEvidence]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )


class FindingEvidence(Base):
    """Many-to-many trace-link between a finding and the evidence rows that
    support it. Immutable once created. The unique constraint is the durable
    guarantee against duplicate links; callers should still dedupe before
    inserting (see app.services.rules.persistence.persist_finding)."""

    __tablename__ = "finding_evidence"
    __table_args__ = (
        UniqueConstraint("finding_id", "evidence_id", name="uq_finding_evidence_finding_evidence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), index=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    finding: Mapped[Finding] = relationship(back_populates="evidence_links")
    evidence: Mapped[Evidence] = relationship()
