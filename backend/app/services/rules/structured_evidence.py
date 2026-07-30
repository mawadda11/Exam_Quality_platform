"""Conservative deterministic evaluators for RULE014, RULE016, and RULE022."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.domain import (
    AcademicStatus,
    AssociationBasis,
    ReferenceResolutionStatus,
    ReferenceTargetType,
    SupportingMaterialType,
)
from app.models.document_reference import DocumentReference
from app.models.evidence import Evidence
from app.models.reference_association import ReferenceAssociation
from app.models.supporting_material import SupportingMaterial
from app.schemas.extraction_review import (
    ExtractionReviewDocumentReference,
    ExtractionReviewSnapshot,
)
from app.services.rules.types import RuleFindingResult


def _evidence_ids(
    session: Session,
    analysis_id: uuid.UUID,
    references: Sequence[DocumentReference],
    materials: Sequence[SupportingMaterial],
) -> list[uuid.UUID]:
    reference_keys = {str(item.id) for item in references}
    material_keys = {str(item.id) for item in materials}
    rows = session.execute(
        select(Evidence).where(
            Evidence.analysis_id == analysis_id,
            (
                (Evidence.evidence_type == "explicit_reference")
                & Evidence.item_reference.in_(reference_keys)
            )
            | (
                Evidence.evidence_type.in_(("figure", "table", "code_block"))
                & Evidence.item_reference.in_(material_keys)
            )
            | (Evidence.evidence_type.in_(("label", "caption"))),
        )
    ).scalars()
    return list(dict.fromkeys(item.id for item in rows))


def _confirmed_rows(
    session: Session,
    analysis_id: uuid.UUID,
    snapshot: ExtractionReviewSnapshot,
    confirmed_revision_id: uuid.UUID,
) -> tuple[
    list[DocumentReference],
    list[SupportingMaterial],
    list[ReferenceAssociation],
]:
    reference_ids = {
        item.source_record_id for item in snapshot.document_references if item.included
    }
    material_ids = {
        item.source_record_id for item in snapshot.supporting_materials if item.included
    }
    references = (
        list(
            session.execute(
                select(DocumentReference).where(DocumentReference.id.in_(reference_ids))
            ).scalars()
        )
        if reference_ids
        else []
    )
    materials = (
        list(
            session.execute(
                select(SupportingMaterial).where(SupportingMaterial.id.in_(material_ids))
            ).scalars()
        )
        if material_ids
        else []
    )
    associations = (
        list(
            session.execute(
                select(ReferenceAssociation).where(
                    ReferenceAssociation.reference_id.in_(reference_ids),
                    ReferenceAssociation.review_revision_id == confirmed_revision_id,
                )
            ).scalars()
        )
        if reference_ids
        else []
    )
    return references, materials, associations


def _confidence(
    references: Sequence[DocumentReference],
    materials: Sequence[SupportingMaterial],
) -> float:
    return min(
        [item.confidence for item in references] + [item.confidence for item in materials],
        default=1.0,
    )


def _selected_reference_ids(
    associations: Sequence[ReferenceAssociation],
) -> set[uuid.UUID]:
    return {
        item.reference_id
        for item in associations
        if item.selected and item.exact_label_match and item.basis is AssociationBasis.EXACT_LABEL
    }


def _proximity_only_reference_ids(
    associations: Sequence[ReferenceAssociation],
    selected_reference_ids: set[uuid.UUID],
) -> set[uuid.UUID]:
    return {
        item.reference_id
        for item in associations
        if item.basis is AssociationBasis.PROXIMITY_SUPPORT
        and item.reference_id not in selected_reference_ids
    }


def _ambiguous_reference_ids(
    references: Sequence[DocumentReference],
    reviewed: dict[uuid.UUID, ExtractionReviewDocumentReference],
) -> set[uuid.UUID]:
    return {
        item.id
        for item in references
        if reviewed[item.id].resolution_status is ReferenceResolutionStatus.AMBIGUOUS
    }


def _reference_labels(
    references: Sequence[DocumentReference],
    reference_ids: set[uuid.UUID],
) -> str:
    return ", ".join(
        dict.fromkeys(item.target_label for item in references if item.id in reference_ids)
    )


def evaluate_referenced_material_availability(
    session: Session,
    *,
    analysis_id: uuid.UUID,
    snapshot: ExtractionReviewSnapshot,
    confirmed_revision_id: uuid.UUID,
) -> RuleFindingResult:
    references, materials, associations = _confirmed_rows(
        session, analysis_id, snapshot, confirmed_revision_id
    )
    material_references = [
        item for item in references if item.target_type is not ReferenceTargetType.QUESTION
    ]
    if not material_references:
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation="No explicit supporting-material reference is used in the exam.",
            confidence=1.0,
            evidence_ids=[],
        )
    reviewed = {
        item.source_record_id: item for item in snapshot.document_references if item.included
    }
    selected_reference_ids = _selected_reference_ids(associations)
    proximity_only_ids = _proximity_only_reference_ids(associations, selected_reference_ids)
    ambiguous_ids = _ambiguous_reference_ids(material_references, reviewed)
    missing_ids = {
        item.id
        for item in material_references
        if item.id not in selected_reference_ids
        and item.id not in ambiguous_ids
        and item.id not in proximity_only_ids
    }
    if ambiguous_ids:
        explanation = (
            "Availability cannot be verified because these references have duplicate or "
            f"non-unique physical targets: {_reference_labels(material_references, ambiguous_ids)}."
        )
        if missing_ids:
            explanation += (
                " These explicitly referenced items are also absent: "
                + _reference_labels(material_references, missing_ids)
                + "."
            )
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=explanation,
            confidence=_confidence(material_references, materials),
            evidence_ids=_evidence_ids(session, analysis_id, material_references, materials),
        )
    unresolved = [item for item in material_references if item.id not in selected_reference_ids]
    if unresolved:
        return RuleFindingResult(
            status=AcademicStatus.NOT_SATISFIED,
            explanation=(
                "One or more explicitly referenced supporting items are absent: "
                + ", ".join(item.target_label for item in unresolved)
                + "."
            ),
            confidence=_confidence(material_references, materials),
            evidence_ids=_evidence_ids(session, analysis_id, material_references, materials),
        )
    selected_material_ids = {
        item.target_material_id
        for item in associations
        if item.selected and item.target_material_id is not None
    }
    selected_materials = [item for item in materials if item.id in selected_material_ids]
    incomplete = [
        item
        for item in selected_materials
        if item.material_type in {SupportingMaterialType.TABLE, SupportingMaterialType.CODE_BLOCK}
        and not item.source_text.strip()
    ]
    if incomplete:
        return RuleFindingResult(
            status=AcademicStatus.PARTIALLY_SATISFIED,
            explanation=(
                "All explicitly referenced supporting items are present, but one extracted "
                "table or code element is incomplete and requires review."
            ),
            confidence=_confidence(material_references, selected_materials),
            evidence_ids=_evidence_ids(
                session, analysis_id, material_references, selected_materials
            ),
        )
    return RuleFindingResult(
        status=AcademicStatus.SATISFIED,
        explanation="All explicitly referenced supporting items resolve to present, unique labels.",
        confidence=_confidence(material_references, selected_materials),
        evidence_ids=_evidence_ids(session, analysis_id, material_references, selected_materials),
    )


def evaluate_supporting_material_association(
    session: Session,
    *,
    analysis_id: uuid.UUID,
    snapshot: ExtractionReviewSnapshot,
    confirmed_revision_id: uuid.UUID,
) -> RuleFindingResult:
    references, materials, associations = _confirmed_rows(
        session, analysis_id, snapshot, confirmed_revision_id
    )
    if not materials:
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation="No supporting material is present in the exam.",
            confidence=1.0,
            evidence_ids=[],
        )
    material_references = [
        item for item in references if item.target_type is not ReferenceTargetType.QUESTION
    ]
    reviewed = {
        item.source_record_id: item for item in snapshot.document_references if item.included
    }
    ambiguous_ids = _ambiguous_reference_ids(material_references, reviewed)
    if ambiguous_ids:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=(
                "A reliable question-to-material association cannot be verified because "
                "distinct physical materials share these reference labels: "
                + _reference_labels(material_references, ambiguous_ids)
                + "."
            ),
            confidence=_confidence(material_references, materials),
            evidence_ids=_evidence_ids(session, analysis_id, material_references, materials),
        )
    associated_material_ids = {
        item.target_material_id
        for item in associations
        if item.selected
        and item.exact_label_match
        and item.target_material_id is not None
        and next(
            reference for reference in material_references if reference.id == item.reference_id
        ).question_id
        is not None
    }
    unassociated = [item for item in materials if item.id not in associated_material_ids]
    if unassociated:
        return RuleFindingResult(
            status=AcademicStatus.NOT_SATISFIED,
            explanation=(
                "One or more supporting items cannot be associated with one intended question "
                "through an exact, explicit reference."
            ),
            confidence=_confidence(material_references, materials),
            evidence_ids=_evidence_ids(session, analysis_id, material_references, materials),
        )
    return RuleFindingResult(
        status=AcademicStatus.SATISFIED,
        explanation=(
            "Every supporting item is associated with an intended question through one exact, "
            "unique explicit reference."
        ),
        confidence=_confidence(material_references, materials),
        evidence_ids=_evidence_ids(session, analysis_id, material_references, materials),
    )


def evaluate_resolvable_cross_references(
    session: Session,
    *,
    analysis_id: uuid.UUID,
    snapshot: ExtractionReviewSnapshot,
    confirmed_revision_id: uuid.UUID,
) -> RuleFindingResult:
    references, materials, associations = _confirmed_rows(
        session, analysis_id, snapshot, confirmed_revision_id
    )
    if not references:
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation="No explicit cross-reference is used in the exam.",
            confidence=1.0,
            evidence_ids=[],
        )
    reviewed = {
        item.source_record_id: item for item in snapshot.document_references if item.included
    }
    selected_reference_ids = _selected_reference_ids(associations)
    proximity_only_ids = _proximity_only_reference_ids(associations, selected_reference_ids)
    ambiguous_ids = _ambiguous_reference_ids(references, reviewed)
    missing_ids = {
        item.id
        for item in references
        if item.id not in selected_reference_ids
        and item.id not in proximity_only_ids
        and item.id not in ambiguous_ids
    }
    if ambiguous_ids:
        explanation = (
            "Cross-references cannot be verified because distinct physical targets share "
            f"these labels: {_reference_labels(references, ambiguous_ids)}."
        )
        if missing_ids:
            explanation += (
                " These explicit references are also missing: "
                + _reference_labels(references, missing_ids)
                + "."
            )
        if proximity_only_ids:
            explanation += (
                " A nearby material is only an advisory candidate; proximity alone does "
                "not resolve its implicit reference."
            )
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=explanation,
            confidence=_confidence(references, materials),
            evidence_ids=_evidence_ids(session, analysis_id, references, materials),
        )
    if proximity_only_ids:
        return RuleFindingResult(
            status=AcademicStatus.NOT_VERIFIED,
            explanation=(
                "At least one cross-reference has proximity candidates but no exact unique "
                "label; proximity alone is insufficient."
            ),
            confidence=_confidence(references, materials),
            evidence_ids=_evidence_ids(session, analysis_id, references, materials),
        )
    unresolved = [item for item in references if item.id in missing_ids]
    if unresolved:
        return RuleFindingResult(
            status=AcademicStatus.NOT_SATISFIED,
            explanation=(
                "One or more explicit cross-references do not resolve to an identifiable item: "
                + ", ".join(item.target_label for item in unresolved)
                + "."
            ),
            confidence=_confidence(references, materials),
            evidence_ids=_evidence_ids(session, analysis_id, references, materials),
        )
    return RuleFindingResult(
        status=AcademicStatus.SATISFIED,
        explanation="Every explicit cross-reference resolves to one exact, identifiable item.",
        confidence=_confidence(references, materials),
        evidence_ids=_evidence_ids(session, analysis_id, references, materials),
    )
