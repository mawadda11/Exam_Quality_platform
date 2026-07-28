"""add structured evidence and capability versioning

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.domain import (
    AssociationBasis,
    ReferenceResolutionStatus,
    ReferenceTargetType,
    SupportingAnnotationType,
    SupportingMaterialType,
    UploadedFileType,
    enum_values,
)

revision: str = "0012"
down_revision: str | None = "0011"
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
    # Deliberately nullable: historical rows remain NULL and resolve to the
    # legacy capability version in application code. No data is backfilled.
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.add_column(sa.Column("capability_version", sa.String(100), nullable=True))
        batch_op.create_index(
            "ix_analyses_capability_version",
            ["capability_version"],
            unique=False,
        )
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("capability_version", sa.String(100), nullable=True))

    op.create_table(
        "supporting_materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("source_document", _enum(UploadedFileType), nullable=False),
        sa.Column("material_type", _enum(SupportingMaterialType), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("extraction_method", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supporting_materials_analysis_id",
        "supporting_materials",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(
        "ix_supporting_materials_question_id",
        "supporting_materials",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        "ix_supporting_materials_material_type",
        "supporting_materials",
        ["material_type"],
        unique=False,
    )

    op.create_table(
        "supporting_material_annotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=True),
        sa.Column("source_document", _enum(UploadedFileType), nullable=False),
        sa.Column("annotation_type", _enum(SupportingAnnotationType), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("normalized_label", sa.String(100), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("extraction_method", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["supporting_materials.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supporting_material_annotations_analysis_id",
        "supporting_material_annotations",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(
        "ix_supporting_material_annotations_material_id",
        "supporting_material_annotations",
        ["material_id"],
        unique=False,
    )
    op.create_index(
        "ix_supporting_material_annotations_normalized_label",
        "supporting_material_annotations",
        ["normalized_label"],
        unique=False,
    )

    op.create_table(
        "document_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("source_document", _enum(UploadedFileType), nullable=False),
        sa.Column("target_type", _enum(ReferenceTargetType), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("target_label", sa.String(100), nullable=False),
        sa.Column("normalized_target_label", sa.String(100), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("extraction_method", sa.String(20), nullable=False),
        sa.Column(
            "machine_resolution_status",
            _enum(ReferenceResolutionStatus),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_references_analysis_id",
        "document_references",
        ["analysis_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_references_question_id",
        "document_references",
        ["question_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_references_normalized_target_label",
        "document_references",
        ["normalized_target_label"],
        unique=False,
    )

    op.create_table(
        "reference_associations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference_id", sa.Uuid(), nullable=False),
        sa.Column("target_material_id", sa.Uuid(), nullable=True),
        sa.Column("target_question_id", sa.Uuid(), nullable=True),
        sa.Column("review_revision_id", sa.Uuid(), nullable=True),
        sa.Column("basis", _enum(AssociationBasis), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("proximity_distance", sa.Float(), nullable=True),
        sa.Column("exact_label_match", sa.Boolean(), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("ambiguity_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(target_material_id IS NOT NULL AND target_question_id IS NULL) OR "
            "(target_material_id IS NULL AND target_question_id IS NOT NULL)",
            name="ck_reference_associations_one_target",
        ),
        sa.ForeignKeyConstraint(
            ["reference_id"],
            ["document_references.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_material_id"],
            ["supporting_materials.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_question_id"],
            ["questions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["review_revision_id"],
            ["extraction_review_revisions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reference_id",
            "target_material_id",
            "target_question_id",
            "review_revision_id",
            "basis",
            name="uq_reference_association_candidate_revision",
        ),
    )
    for column in (
        "reference_id",
        "target_material_id",
        "target_question_id",
        "review_revision_id",
    ):
        op.create_index(
            f"ix_reference_associations_{column}",
            "reference_associations",
            [column],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("reference_associations")
    op.drop_table("document_references")
    op.drop_table("supporting_material_annotations")
    op.drop_table("supporting_materials")
    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_column("capability_version")
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_index("ix_analyses_capability_version")
        batch_op.drop_column("capability_version")
