"""create core tables

Revision ID: 0001
Revises:
Create Date: 2026-07-22

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.domain import ExamType, ProcessingStage, UploadedFileType, UserType, enum_values

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("institution", sa.String(200), nullable=True),
        sa.Column("department", sa.String(200), nullable=True),
        sa.Column(
            "user_type",
            sa.Enum(
                UserType, native_enum=False, validate_strings=True, values_callable=enum_values
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("department", sa.String(200), nullable=True),
        sa.Column("program", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "analyses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.Uuid(as_uuid=True), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column(
            "exam_type",
            sa.Enum(
                ExamType, native_enum=False, validate_strings=True, values_callable=enum_values
            ),
            nullable=False,
        ),
        sa.Column("term", sa.String(50), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                ProcessingStage,
                native_enum=False,
                validate_strings=True,
                values_callable=enum_values,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analyses_user_id", "analyses", ["user_id"])
    op.create_index("ix_analyses_course_id", "analyses", ["course_id"])

    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_type",
            sa.Enum(
                UploadedFileType,
                native_enum=False,
                validate_strings=True,
                values_callable=enum_values,
            ),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "analysis_id", "file_type", name="uq_uploaded_files_analysis_id_file_type"
        ),
    )
    op.create_index("ix_uploaded_files_analysis_id", "uploaded_files", ["analysis_id"])


def downgrade() -> None:
    op.drop_table("uploaded_files")
    op.drop_table("analyses")
    op.drop_table("courses")
    op.drop_table("users")
