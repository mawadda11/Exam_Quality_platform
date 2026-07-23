"""create questions and evidence tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.domain import UploadedFileType, enum_values

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_question_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("number_label", sa.String(50), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("marks", sa.Float(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questions_analysis_id", "questions", ["analysis_id"])
    op.create_index("ix_questions_parent_question_id", "questions", ["parent_question_id"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("questions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_document",
            sa.Enum(
                UploadedFileType,
                native_enum=False,
                validate_strings=True,
                values_callable=enum_values,
            ),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(100), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("item_reference", sa.String(100), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_analysis_id", "evidence", ["analysis_id"])
    op.create_index("ix_evidence_question_id", "evidence", ["question_id"])


def downgrade() -> None:
    op.drop_table("evidence")
    op.drop_table("questions")
