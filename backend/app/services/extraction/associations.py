"""Deterministic exact-label association with proximity retained as non-decisive provenance."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.domain import (
    AssociationBasis,
    ReferenceResolutionStatus,
    ReferenceTargetType,
    SupportingMaterialType,
)
from app.models.document_reference import DocumentReference
from app.models.question import Question
from app.models.reference_association import ReferenceAssociation
from app.models.supporting_material import SupportingMaterial
from app.models.supporting_material_annotation import SupportingMaterialAnnotation
from app.services.extraction.structured_evidence import (
    normalize_question_label,
    normalize_target_label,
)

if TYPE_CHECKING:
    from app.schemas.extraction_review import ExtractionReviewSnapshot


def _center(geometry: dict[str, float] | None) -> tuple[float, float] | None:
    if geometry is None:
        return None
    return (
        (float(geometry["x0"]) + float(geometry["x1"])) / 2,
        (float(geometry["top"]) + float(geometry["bottom"])) / 2,
    )


def _distance(left: dict[str, float] | None, right: dict[str, float] | None) -> float | None:
    left_center = _center(left)
    right_center = _center(right)
    if left_center is None or right_center is None:
        return None
    distance_value = (
        (left_center[0] - right_center[0]) ** 2 + (left_center[1] - right_center[1]) ** 2
    ) ** 0.5
    return round(float(distance_value), 4)


def _question_label(question: Question) -> str | None:
    digits = "".join(character for character in question.number_label if character.isdigit())
    return normalize_question_label(digits) if digits else None


def _material_type(target_type: ReferenceTargetType) -> SupportingMaterialType | None:
    if target_type is ReferenceTargetType.QUESTION:
        return None
    return SupportingMaterialType(target_type.value)


def materialize_reference_associations(
    session: Session,
    *,
    analysis_id: UUID,
    references: Sequence[DocumentReference] | None = None,
    review_revision_id: UUID | None = None,
) -> list[ReferenceAssociation]:
    """Persist every exact candidate plus bounded proximity-only provenance.

    A candidate is selected only when an exact label resolves to one unique
    target. Proximity records are never selected and never change resolution.
    """

    reference_rows = list(
        references
        if references is not None
        else session.execute(
            select(DocumentReference).where(DocumentReference.analysis_id == analysis_id)
        ).scalars()
    )
    materials = list(
        session.execute(
            select(SupportingMaterial).where(SupportingMaterial.analysis_id == analysis_id)
        ).scalars()
    )
    annotations = list(
        session.execute(
            select(SupportingMaterialAnnotation).where(
                SupportingMaterialAnnotation.analysis_id == analysis_id
            )
        ).scalars()
    )
    questions = list(
        session.execute(select(Question).where(Question.analysis_id == analysis_id)).scalars()
    )
    material_by_id = {item.id: item for item in materials}
    created: list[ReferenceAssociation] = []

    for reference in reference_rows:
        exact_material_ids: list[UUID] = []
        exact_question_ids: list[UUID] = []
        if reference.target_type is ReferenceTargetType.QUESTION:
            exact_question_ids = [
                question.id
                for question in questions
                if _question_label(question) == reference.normalized_target_label
            ]
        else:
            exact_material_ids = list(
                dict.fromkeys(
                    annotation.material_id
                    for annotation in annotations
                    if annotation.material_id is not None
                    and annotation.normalized_label == reference.normalized_target_label
                    and material_by_id[annotation.material_id].material_type.value
                    == reference.target_type.value
                )
            )

        exact_count = len(exact_material_ids) + len(exact_question_ids)
        status = (
            ReferenceResolutionStatus.RESOLVED
            if exact_count == 1
            else (
                ReferenceResolutionStatus.AMBIGUOUS
                if exact_count > 1
                else ReferenceResolutionStatus.UNRESOLVED
            )
        )
        if review_revision_id is None:
            reference.machine_resolution_status = status
        ambiguity_reason = (
            f"{exact_count} exact targets share this label." if exact_count > 1 else None
        )
        for material_id in exact_material_ids:
            material = material_by_id[material_id]
            association = ReferenceAssociation(
                reference_id=reference.id,
                target_material_id=material_id,
                target_question_id=None,
                review_revision_id=review_revision_id,
                basis=AssociationBasis.EXACT_LABEL,
                confidence=min(reference.confidence, material.confidence),
                exact_label_match=True,
                selected=exact_count == 1,
                ambiguity_reason=ambiguity_reason,
            )
            session.add(association)
            created.append(association)
        for question_id in exact_question_ids:
            question = next(item for item in questions if item.id == question_id)
            association = ReferenceAssociation(
                reference_id=reference.id,
                target_material_id=None,
                target_question_id=question_id,
                review_revision_id=review_revision_id,
                basis=AssociationBasis.EXACT_LABEL,
                confidence=min(reference.confidence, question.confidence),
                exact_label_match=True,
                selected=exact_count == 1,
                ambiguity_reason=ambiguity_reason,
            )
            session.add(association)
            created.append(association)

        target_material_type = _material_type(reference.target_type)
        if target_material_type is None:
            continue
        exact_set = set(exact_material_ids)
        proximity = [
            (distance, material)
            for material in materials
            if material.material_type is target_material_type
            and material.page_number == reference.page_number
            and material.id not in exact_set
            and (distance := _distance(reference.geometry, material.geometry)) is not None
        ]
        for distance, material in sorted(proximity, key=lambda item: item[0])[:3]:
            association = ReferenceAssociation(
                reference_id=reference.id,
                target_material_id=material.id,
                target_question_id=None,
                review_revision_id=review_revision_id,
                basis=AssociationBasis.PROXIMITY_SUPPORT,
                confidence=min(reference.confidence, material.confidence, 0.5),
                proximity_distance=distance,
                exact_label_match=False,
                selected=False,
                ambiguity_reason="Proximity is supporting evidence only.",
            )
            session.add(association)
            created.append(association)
    session.flush()
    return created


def materialize_confirmed_reference_associations(
    session: Session,
    *,
    analysis_id: UUID,
    snapshot: ExtractionReviewSnapshot,
    review_revision_id: UUID,
) -> list[ReferenceAssociation]:
    """Persist revision-linked candidates from the confirmed review values."""

    references = {
        item.id: item
        for item in session.execute(
            select(DocumentReference).where(DocumentReference.analysis_id == analysis_id)
        ).scalars()
    }
    materials = {
        item.id: item
        for item in session.execute(
            select(SupportingMaterial).where(SupportingMaterial.analysis_id == analysis_id)
        ).scalars()
    }
    questions = {
        item.id: item
        for item in session.execute(
            select(Question).where(Question.analysis_id == analysis_id)
        ).scalars()
    }
    included_material_ids = {
        item.source_record_id for item in snapshot.supporting_materials if item.included
    }
    included_question_ids = {item.source_record_id for item in snapshot.questions if item.included}
    annotations = [
        item
        for item in snapshot.supporting_annotations
        if item.included
        and item.material_source_record_id is not None
        and item.material_source_record_id in included_material_ids
    ]
    question_snapshot = {
        item.source_record_id: item for item in snapshot.questions if item.included
    }
    created: list[ReferenceAssociation] = []

    for reviewed_reference in snapshot.document_references:
        if not reviewed_reference.included:
            continue
        reference = references[reviewed_reference.source_record_id]
        material_ids: list[UUID] = []
        question_ids: list[UUID] = []
        if reviewed_reference.target_type is ReferenceTargetType.QUESTION:
            question_ids = [
                question_id
                for question_id, question in question_snapshot.items()
                if normalize_target_label(
                    ReferenceTargetType.QUESTION,
                    question.number_label,
                )
                == reviewed_reference.normalized_target_label
                and question_id in included_question_ids
            ]
        else:
            material_ids = list(
                dict.fromkeys(
                    annotation.material_source_record_id
                    for annotation in annotations
                    if annotation.normalized_label == reviewed_reference.normalized_target_label
                    and annotation.material_source_record_id is not None
                    and materials[annotation.material_source_record_id].material_type.value
                    == reviewed_reference.target_type.value
                )
            )
        exact_count = len(material_ids) + len(question_ids)
        ambiguity_reason = (
            f"{exact_count} exact targets share this label." if exact_count > 1 else None
        )
        for material_id in material_ids:
            material_target = materials[material_id]
            row = ReferenceAssociation(
                reference_id=reference.id,
                target_material_id=material_id,
                target_question_id=None,
                review_revision_id=review_revision_id,
                basis=AssociationBasis.EXACT_LABEL,
                confidence=min(
                    reviewed_reference.extraction_confidence,
                    material_target.confidence,
                ),
                exact_label_match=True,
                selected=exact_count == 1,
                ambiguity_reason=ambiguity_reason,
            )
            session.add(row)
            created.append(row)
        for question_id in question_ids:
            question_target = questions[question_id]
            row = ReferenceAssociation(
                reference_id=reference.id,
                target_material_id=None,
                target_question_id=question_id,
                review_revision_id=review_revision_id,
                basis=AssociationBasis.EXACT_LABEL,
                confidence=min(
                    reviewed_reference.extraction_confidence,
                    question_target.confidence,
                ),
                exact_label_match=True,
                selected=exact_count == 1,
                ambiguity_reason=ambiguity_reason,
            )
            session.add(row)
            created.append(row)

        target_material_type = _material_type(reviewed_reference.target_type)
        if target_material_type is None:
            continue
        exact_set = set(material_ids)
        proximity = [
            (distance, material)
            for material_id, material in materials.items()
            if material_id in included_material_ids
            and material.material_type is target_material_type
            and material.page_number == reviewed_reference.page_number
            and material.id not in exact_set
            and (distance := _distance(reference.geometry, material.geometry)) is not None
        ]
        for distance, material in sorted(proximity, key=lambda item: item[0])[:3]:
            row = ReferenceAssociation(
                reference_id=reference.id,
                target_material_id=material.id,
                target_question_id=None,
                review_revision_id=review_revision_id,
                basis=AssociationBasis.PROXIMITY_SUPPORT,
                confidence=min(
                    reviewed_reference.extraction_confidence,
                    material.confidence,
                    0.5,
                ),
                proximity_distance=distance,
                exact_label_match=False,
                selected=False,
                ambiguity_reason="Proximity is supporting evidence only.",
            )
            session.add(row)
            created.append(row)
    session.flush()
    return created
