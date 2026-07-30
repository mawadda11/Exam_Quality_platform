"""add bilingual extraction metadata

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("uploaded_files") as batch_op:
        batch_op.add_column(sa.Column("detected_language", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("extraction_method", sa.String(20), nullable=True))
        batch_op.add_column(sa.Column("extraction_confidence", sa.Float(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "review_recommended",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("parser_layout", sa.String(40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("uploaded_files") as batch_op:
        batch_op.drop_column("parser_layout")
        batch_op.drop_column("review_recommended")
        batch_op.drop_column("extraction_confidence")
        batch_op.drop_column("extraction_method")
        batch_op.drop_column("detected_language")
