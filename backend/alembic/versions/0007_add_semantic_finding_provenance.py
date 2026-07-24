"""add semantic finding provenance and duplicate protection

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("findings") as batch_op:
        batch_op.add_column(sa.Column("recommendation_id", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("ai_provider", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("ai_model", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("prompt_template_version", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("kb_version", sa.String(50), nullable=True))
        batch_op.create_unique_constraint(
            "uq_findings_analysis_id_rule_id", ["analysis_id", "rule_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("findings") as batch_op:
        batch_op.drop_constraint("uq_findings_analysis_id_rule_id", type_="unique")
        batch_op.drop_column("kb_version")
        batch_op.drop_column("prompt_template_version")
        batch_op.drop_column("ai_model")
        batch_op.drop_column("ai_provider")
        batch_op.drop_column("recommendation_id")
