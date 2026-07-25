"""add extraction review persistence foundation

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.domain import SemanticConfidenceLevel, enum_values

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "extraction_review_revisions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "revision_number >= 1",
            name="ck_extraction_review_revisions_positive_revision",
        ),
        sa.UniqueConstraint(
            "analysis_id",
            "revision_number",
            name="uq_extraction_review_revisions_analysis_revision",
        ),
    )

    with op.batch_alter_table("analyses") as batch_op:
        batch_op.add_column(sa.Column("confirmed_review_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_analyses_confirmed_review_id_extraction_review_revisions",
            "extraction_review_revisions",
            ["confirmed_review_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_analyses_confirmed_review_id",
            ["confirmed_review_id"],
        )

    with op.batch_alter_table("findings") as batch_op:
        batch_op.add_column(
            sa.Column(
                "confidence_level",
                sa.Enum(
                    SemanticConfidenceLevel,
                    native_enum=False,
                    validate_strings=True,
                    values_callable=enum_values,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("evaluation_details", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("findings") as batch_op:
        batch_op.drop_column("evaluation_details")
        batch_op.drop_column("confidence_level")

    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_constraint("uq_analyses_confirmed_review_id", type_="unique")
        batch_op.drop_constraint(
            "fk_analyses_confirmed_review_id_extraction_review_revisions",
            type_="foreignkey",
        )
        batch_op.drop_column("confirmed_review_id")

    op.drop_table("extraction_review_revisions")
