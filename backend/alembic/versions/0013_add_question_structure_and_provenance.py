"""add question structure, options, blanks, provenance, and extraction warnings

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.domain import (
    ExtractionWarningSeverity,
    QuestionReviewStatus,
    QuestionType,
    enum_values,
)

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(enum_cls: type) -> sa.Enum:
    return sa.Enum(
        enum_cls,
        native_enum=False,
        validate_strings=True,
        values_callable=enum_values,
    )


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "question_type",
                _enum(QuestionType),
                nullable=False,
                server_default=QuestionType.UNKNOWN.value,
            )
        )
        batch_op.add_column(sa.Column("instructions", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "extraction_method",
                sa.String(30),
                nullable=False,
                server_default="legacy",
            )
        )
        batch_op.add_column(
            sa.Column(
                "review_status",
                _enum(QuestionReviewStatus),
                nullable=False,
                server_default=QuestionReviewStatus.REVIEWED.value,
            )
        )

    op.create_table(
        "question_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("option_label", sa.String(50), nullable=False),
        sa.Column("option_text", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_question_options_question_id", "question_options", ["question_id"], unique=False
    )

    op.create_table(
        "question_blanks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("blank_index", sa.Integer(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_question_blanks_question_id", "question_blanks", ["question_id"], unique=False
    )

    op.create_table(
        "question_source_spans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("option_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_version", sa.String(100), nullable=True),
        sa.Column("source_line_id", sa.String(100), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("extraction_method", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["option_id"], ["question_options.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("question_id", "option_id", "source_line_id"):
        op.create_index(
            f"ix_question_source_spans_{column}",
            "question_source_spans",
            [column],
            unique=False,
        )

    op.create_table(
        "extraction_warnings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("severity", _enum(ExtractionWarningSeverity), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("source_line_ids", sa.JSON(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extraction_warnings_analysis_id",
        "extraction_warnings",
        ["analysis_id"],
        unique=False,
    )
    op.create_index("ix_extraction_warnings_code", "extraction_warnings", ["code"], unique=False)


def downgrade() -> None:
    op.drop_table("extraction_warnings")
    op.drop_table("question_source_spans")
    op.drop_table("question_blanks")
    op.drop_table("question_options")
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_column("review_status")
        batch_op.drop_column("extraction_method")
        batch_op.drop_column("instructions")
        batch_op.drop_column("question_type")
