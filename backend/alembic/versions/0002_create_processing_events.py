"""create processing_events table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.domain import ProcessingStage, enum_values

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processing_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stage",
            sa.Enum(
                ProcessingStage,
                native_enum=False,
                validate_strings=True,
                values_callable=enum_values,
            ),
            nullable=False,
        ),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_processing_events_analysis_id", "processing_events", ["analysis_id"])


def downgrade() -> None:
    op.drop_table("processing_events")
