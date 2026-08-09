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
        if item.selected and (
            (item.exact_label_match and item.basis is AssociationBasis.EXACT_LABEL)
            or item.basis in {AssociationBasis.DEICTIC_GEOMETRY, AssociationBasis.AI_ADJUDICATION}
        )
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


def _is_contextual_reference(reference: DocumentReference) -> bool:
    """Return True for non-numbered/deictic references kept only for faculty review."""
    return reference.normalized_target_label.endswith(":unlabeled")


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
    all_material_references = [
        item for item in references if item.target_type is not ReferenceTargetType.QUESTION
    ]
    material_references = [
        item for item in all_material_references if not _is_contextual_reference(item)
    ]
    if not material_references:
        explanation = (
            "Only contextual supporting-material references were detected; they are shown "
            "for faculty review and are intentionally excluded from automatic scoring."
            if all_material_references
            else "No explicit supporting-material reference is used in the exam."
        )
        return RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation=explanation,
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

    if missing_ids or ambiguous_ids:
        parts: list[str] = []
        if missing_ids:
            parts.append(
                "explicitly referenced supporting items are absent: "
                + _reference_labels(material_references, missing_ids)
            )
        if ambiguous_ids:
            parts.append(
                "explicit labels do not identify a unique physical target: "
                + _reference_labels(material_references, ambiguous_ids)
            )
        return RuleFindingResult(
            status=AcademicStatus.NOT_SATISFIED,
            explanation="; ".join(parts).capitalize() + ".",
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

    explicit_reference_ids = {item.id for item in material_references}
    selected_material_ids = {
        item.target_material_id
        for item in associations
        if item.selected
        and item.reference_id in explicit_reference_ids
        and item.target_material_id is not None
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
                "All explicit supporting-material references resolve, but one extracted "
                "table or code element is incomplete and requires faculty review."
            ),
            confidence=_confidence(material_references, selected_materials),
            evidence_ids=_evidence_ids(
                session, analysis_id, material_references, selected_materials
            ),
        )
    return RuleFindingResult(
        status=AcademicStatus.SATISFIED,
        explanation="All explicit supporting-material references resolve to present, unique targets.",
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
    # Pilot scope decision: the Materials & References page already exposes
    # the association detail.  Scoring it again would double-count the same
    # missing/duplicate-reference defect covered by RULE014.
    return RuleFindingResult(
        status=AcademicStatus.NOT_APPLICABLE,
        explanation=(
            "Detailed question-to-material association remains available in Materials & "
            "References, but this duplicate meta-rule is outside automatic pilot scoring."
        ),
        confidence=1.0,
        evidence_ids=[],
    )

def evaluate_resolvable_cross_references(
    session: Session,
    *,
    analysis_id: uuid.UUID,
    snapshot: ExtractionReviewSnapshot,
    confirmed_revision_id: uuid.UUID,
) -> RuleFindingResult:
    # Pilot scope decision: resolution detail is visible per reference in the
    # Materials & References view.  RULE014 is the single scored material rule
    # so the same defect is not penalized multiple times.
    return RuleFindingResult(
        status=AcademicStatus.NOT_APPLICABLE,
        explanation=(
            "Cross-reference resolution detail remains available in Materials & References, "
            "but this duplicate meta-rule is outside automatic pilot scoring."
        ),
        confidence=1.0,
        evidence_ids=[],
    )

