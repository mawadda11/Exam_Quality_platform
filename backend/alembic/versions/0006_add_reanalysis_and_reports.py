"""add predecessor_analysis_id and reports table (M10)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.domain import ReportFormat, enum_values

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # batch_alter_table: SQLite cannot ALTER TABLE ADD COLUMN with a new
    # foreign-key constraint directly (only via its copy-and-move "batch"
    # strategy) - Postgres performs a normal, direct ALTER TABLE either way,
    # so this stays the portable way to write it for both.
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.add_column(sa.Column("predecessor_analysis_id", sa.Uuid(as_uuid=True)))
        batch_op.create_foreign_key(
            "fk_analyses_predecessor_analysis_id_analyses",
            "analyses",
            ["predecessor_analysis_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_analyses_predecessor_analysis_id", ["predecessor_analysis_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "format",
            sa.Enum(
                ReportFormat, native_enum=False, validate_strings=True, values_callable=enum_values
            ),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("kb_version", sa.String(50), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("score_label", sa.String(50), nullable=True),
        sa.Column("denominator", sa.Integer(), nullable=False),
        sa.Column("satisfied_count", sa.Integer(), nullable=False),
        sa.Column("partially_satisfied_count", sa.Integer(), nullable=False),
        sa.Column("not_satisfied_count", sa.Integer(), nullable=False),
        sa.Column("not_verified_count", sa.Integer(), nullable=False),
        sa.Column("not_applicable_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_analysis_id", "reports", ["analysis_id"])


def downgrade() -> None:
    op.drop_table("reports")
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_index("ix_analyses_predecessor_analysis_id")
        batch_op.drop_constraint("fk_analyses_predecessor_analysis_id_analyses", type_="foreignkey")
        batch_op.drop_column("predecessor_analysis_id")
