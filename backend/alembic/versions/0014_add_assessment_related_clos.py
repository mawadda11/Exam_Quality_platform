"""add assessment related CLO identifiers

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("assessment_records") as batch_op:
        batch_op.add_column(sa.Column("related_clo_codes", sa.JSON(), nullable=False, server_default="[]"))

def downgrade() -> None:
    with op.batch_alter_table("assessment_records") as batch_op:
        batch_op.drop_column("related_clo_codes")
