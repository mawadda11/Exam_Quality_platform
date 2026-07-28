"""add Batch 3 language and retry metadata

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.domain import LanguageCode, ProcessingStage, ReportLanguage, enum_values

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "preferred_language",
                sa.Enum(
                    LanguageCode,
                    native_enum=False,
                    validate_strings=True,
                    values_callable=enum_values,
                ),
                nullable=False,
                server_default=LanguageCode.ARABIC.value,
            )
        )

    with op.batch_alter_table("processing_events") as batch_op:
        batch_op.add_column(
            sa.Column(
                "failed_stage",
                sa.Enum(
                    ProcessingStage,
                    native_enum=False,
                    validate_strings=True,
                    values_callable=enum_values,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("error_code", sa.String(100), nullable=True))
        batch_op.add_column(
            sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(
            sa.Column(
                "language",
                sa.Enum(
                    ReportLanguage,
                    native_enum=False,
                    validate_strings=True,
                    values_callable=enum_values,
                ),
                nullable=False,
                server_default=ReportLanguage.ENGLISH.value,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_column("language")
    with op.batch_alter_table("processing_events") as batch_op:
        batch_op.drop_column("retryable")
        batch_op.drop_column("error_code")
        batch_op.drop_column("failed_stage")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("preferred_language")
