"""create findings and finding_evidence tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.domain import AcademicStatus, enum_values

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requirement_id", sa.String(50), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                AcademicStatus,
                native_enum=False,
                validate_strings=True,
                values_callable=enum_values,
            ),
            nullable=False,
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evaluator_type", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_findings_analysis_id", "findings", ["analysis_id"])

    op.create_table(
        "finding_evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "finding_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("evidence.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "finding_id", "evidence_id", name="uq_finding_evidence_finding_evidence"
        ),
    )
    op.create_index("ix_finding_evidence_finding_id", "finding_evidence", ["finding_id"])


def downgrade() -> None:
    op.drop_table("finding_evidence")
    op.drop_table("findings")
