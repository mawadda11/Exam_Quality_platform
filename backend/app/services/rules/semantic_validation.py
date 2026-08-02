"""Deterministic validation gate for untrusted semantic model output."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.domain import AcademicStatus, SemanticConfidenceLevel, UploadedFileType
from app.models.analysis import Analysis
from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.topic import Topic
from app.services.ai.provider import AiProvider
from app.services.knowledge_base.reference_data import (
    get_recommendation_by_id,
    get_recommendations_for,
)
from app.services.rules.semantic_types import (
    SemanticAiOutput,
    SemanticItemJudgment,
    SemanticValidationContext,
    ValidatedSemanticResult,
)


class SemanticOutputValidationError(RuntimeError):
    """Invalid model output is never released as an academic finding."""


def semantic_output_schema() -> dict[str, object]:
    return SemanticAiOutput.model_json_schema()


def aggregate_item_statuses(items: Sequence[SemanticItemJudgment]) -> AcademicStatus:
    """Deterministically aggregate item judgments using only approved statuses.

    This is intentionally threshold-free. All-equal cases preserve the item
    status. Mixed scorable outcomes become Partially Satisfied. Not Applicable
    items are ignored when another substantive item exists; an all-N/A set is
    Not Applicable. A mixture containing Not Verified and at least one usable
    judgment is Partially Satisfied, while an all-Not-Verified set remains Not
    Verified.
    """

    statuses = [item.status for item in items]
    if not statuses:
        return AcademicStatus.NOT_VERIFIED
    if all(status is AcademicStatus.NOT_APPLICABLE for status in statuses):
        return AcademicStatus.NOT_APPLICABLE

    substantive = [status for status in statuses if status is not AcademicStatus.NOT_APPLICABLE]
    if not substantive:
        return AcademicStatus.NOT_APPLICABLE
    if all(status is substantive[0] for status in substantive):
        return substantive[0]
    if all(status is AcademicStatus.NOT_VERIFIED for status in substantive):
        return AcademicStatus.NOT_VERIFIED
    return AcademicStatus.PARTIALLY_SATISFIED


def _validate_extraction_provenance(
    evidence_rows: list[Evidence],
    *,
    session: Session,
    context: SemanticValidationContext,
) -> None:
    """Cross-check semantic citations against their confirmed domain rows."""

    for evidence in evidence_rows:
        if evidence.evidence_type == "question_text":
            if evidence.source_document is not UploadedFileType.EXAM:
                raise SemanticOutputValidationError(
                    "Question evidence does not originate from the exam."
                )
            exists = session.execute(
                select(Question.id).where(
                    Question.analysis_id == context.analysis_id,
                    Question.id == evidence.question_id,
                    Question.number_label == evidence.item_reference,
                    Question.question_text == evidence.extracted_text,
                    Question.page_number == evidence.page_number,
                )
            ).first()
            if exists is None:
                raise SemanticOutputValidationError(
                    "Question evidence has no matching confirmed question."
                )
        elif evidence.evidence_type == "clo":
            if evidence.source_document is not UploadedFileType.TP153:
                raise SemanticOutputValidationError(
                    "CLO evidence does not originate from the TP-153."
                )
            exists = session.execute(
                select(Clo.id).where(
                    Clo.analysis_id == context.analysis_id,
                    Clo.code == evidence.item_reference,
                    Clo.text == evidence.extracted_text,
                    Clo.page_number == evidence.page_number,
                )
            ).first()
            if exists is None:
                raise SemanticOutputValidationError("CLO evidence has no matching confirmed CLO.")
        elif evidence.evidence_type == "topic":
            if evidence.source_document is not UploadedFileType.TP153:
                raise SemanticOutputValidationError(
                    "Topic evidence does not originate from the TP-153."
                )
            exists = session.execute(
                select(Topic.id).where(
                    Topic.analysis_id == context.analysis_id,
                    Topic.text == evidence.extracted_text,
                    Topic.page_number == evidence.page_number,
                )
            ).first()
            if exists is None:
                raise SemanticOutputValidationError(
                    "Topic evidence has no matching confirmed topic."
                )
        elif evidence.evidence_type == "assessment_record":
            if evidence.source_document is not UploadedFileType.TP153:
                raise SemanticOutputValidationError(
                    "Assessment evidence does not originate from the TP-153."
                )
            exists = session.execute(
                select(AssessmentRecord.id).where(
                    AssessmentRecord.analysis_id == context.analysis_id,
                    AssessmentRecord.page_number == evidence.page_number,
                )
            ).first()
            if exists is None:
                raise SemanticOutputValidationError(
                    "Assessment evidence has no matching confirmed assessment record."
                )
        elif evidence.evidence_type == "exam_metadata":
            if evidence.source_document is not UploadedFileType.EXAM:
                raise SemanticOutputValidationError(
                    "Exam metadata evidence does not originate from the exam analysis."
                )
            analysis = session.get(Analysis, context.analysis_id)
            if analysis is None or evidence.item_reference != "exam_type":
                raise SemanticOutputValidationError("Exam metadata evidence is invalid.")
            if analysis.exam_type.value not in evidence.extracted_text:
                raise SemanticOutputValidationError(
                    "Exam metadata evidence does not match the analysis exam type."
                )
        elif evidence.evidence_type == "instructions":
            if evidence.source_document is not UploadedFileType.EXAM:
                raise SemanticOutputValidationError(
                    "Instruction evidence does not originate from the exam."
                )


def _derive_confidence(
    *,
    items: Sequence[SemanticItemJudgment],
    context: SemanticValidationContext,
) -> tuple[SemanticConfidenceLevel, tuple[str, ...]]:
    source_ids = [item.source_evidence_id for item in items]
    source_set = set(source_ids)
    required = set(context.required_source_evidence_ids)

    if len(source_ids) != len(source_set):
        raise SemanticOutputValidationError(
            "Provider output contains duplicate source item judgments."
        )
    if not source_set.issubset(required):
        raise SemanticOutputValidationError(
            "Provider output contains a source evidence item outside the governed source set."
        )

    missing = required - source_set
    if missing:
        return (
            SemanticConfidenceLevel.LOW,
            (
                "One or more required confirmed source items were not judged.",
                f"Missing source judgments: {len(missing)}.",
            ),
        )
    if all(item.status is AcademicStatus.NOT_VERIFIED for item in items):
        return (
            SemanticConfidenceLevel.LOW,
            (
                "Every item judgment remained Not Verified.",
                "No releasable semantic relationship was established.",
            ),
        )
    if any(item.status is AcademicStatus.NOT_VERIFIED for item in items):
        return (
            SemanticConfidenceLevel.MEDIUM,
            (
                "Every required source item was judged.",
                "At least one item remained Not Verified while other evidence was usable.",
            ),
        )
    return (
        SemanticConfidenceLevel.HIGH,
        (
            "Every required confirmed source item has exactly one validated judgment.",
            "All cited targets are controlled evidence rows from the same analysis.",
        ),
    )


def _legacy_confidence(level: SemanticConfidenceLevel) -> float:
    """Compatibility value for the legacy non-null database/API column.

    It is derived from the authoritative categorical contract, never from OCR
    or model-supplied numeric confidence. M10 replaces presentation of this
    compatibility field with the categorical value.
    """

    return {
        SemanticConfidenceLevel.HIGH: 1.0,
        SemanticConfidenceLevel.MEDIUM: 0.5,
        SemanticConfidenceLevel.LOW: 0.0,
    }[level]


def validate_semantic_output(
    raw_output: str,
    *,
    session: Session,
    context: SemanticValidationContext,
    provider: AiProvider,
    kb_source_dir: Path,
) -> ValidatedSemanticResult:
    try:
        output = SemanticAiOutput.model_validate_json(raw_output)
    except (ValidationError, TypeError) as exc:
        raise SemanticOutputValidationError("Provider output failed schema validation.") from exc

    spec = context.rule_spec
    if output.rule_id != spec.identifier.rule_id:
        raise SemanticOutputValidationError("Provider output contains an invalid rule ID.")
    if output.requirement_id != spec.identifier.requirement_id:
        raise SemanticOutputValidationError("Provider output contains an invalid requirement ID.")
    if output.provider != provider.provider_name or output.model != provider.model_name:
        raise SemanticOutputValidationError("Provider/model provenance does not match the adapter.")
    if output.prompt_template_version != context.prompt_template_version:
        raise SemanticOutputValidationError("Prompt-template version does not match.")
    if output.kb_version != context.kb_version:
        raise SemanticOutputValidationError("Knowledge-base version does not match.")

    items = tuple(
        item.model_copy(
            update={
                "status": AcademicStatus.NOT_VERIFIED,
                "reasoning": (
                    "Not verified because the provider returned a positive "
                    "relationship without a controlled target."
                ),
            }
        )
        if (
            context.relationship_required
            and item.status
            in (
                AcademicStatus.SATISFIED,
                AcademicStatus.PARTIALLY_SATISFIED,
            )
            and not item.target_evidence_ids
        )
        else item
        for item in output.items
    )

    item_ids: set[UUID] = set()
    for item in items:
        item_ids.add(item.source_evidence_id)
        target_ids = set(item.target_evidence_ids)
        if not target_ids.issubset(context.allowed_target_evidence_ids):
            raise SemanticOutputValidationError(
                "Provider output cites a target outside the governed target set."
            )
        item_ids.update(target_ids)

    if not item_ids:
        raise SemanticOutputValidationError("Semantic findings require at least one evidence ID.")
    if not item_ids.issubset(context.allowed_evidence_ids):
        raise SemanticOutputValidationError("Provider output cites evidence outside its context.")

    # The authoritative evidence list is derived from the validated item
    # judgments. The provider top-level evidence_ids field is advisory.
    evidence_ids = sorted(item_ids, key=str)

    evidence_rows = list(
        session.execute(select(Evidence).where(Evidence.id.in_(item_ids))).scalars().all()
    )
    if len(evidence_rows) != len(item_ids):
        raise SemanticOutputValidationError("Provider output cites unknown evidence.")
    if any(row.analysis_id != context.analysis_id for row in evidence_rows):
        raise SemanticOutputValidationError(
            "Provider output cites evidence owned by another analysis."
        )
    if any(row.evidence_type not in context.allowed_evidence_types for row in evidence_rows):
        raise SemanticOutputValidationError(
            "Provider output cites evidence incompatible with this evaluator."
        )
    _validate_extraction_provenance(evidence_rows, session=session, context=context)

    confidence_level, confidence_basis = _derive_confidence(items=items, context=context)
    aggregate_status = aggregate_item_statuses(items)
    final_status = (
        AcademicStatus.NOT_VERIFIED
        if confidence_level is SemanticConfidenceLevel.LOW
        else aggregate_status
    )
    if final_status not in spec.allowed_statuses:
        raise SemanticOutputValidationError(
            "The deterministically aggregated status is not allowed for this rule."
        )
    # The final status is derived deterministically from the validated
    # item judgments. The provider top-level status is advisory and must
    # not override or block the backend-attested result.

    eligible = {
        item.recommendation_id
        for item in get_recommendations_for(
            kb_source_dir.resolve(), spec.identifier.rule_id, final_status
        )
    }
    if output.recommendation_id is not None and output.recommendation_id not in eligible:
        raise SemanticOutputValidationError(
            "Provider output cites a recommendation that does not apply to the final status."
        )
    if output.recommendation_id is not None:
        recommendation = get_recommendation_by_id(kb_source_dir.resolve(), output.recommendation_id)
        if recommendation is None or recommendation.rule_id != spec.identifier.rule_id:
            raise SemanticOutputValidationError("Provider output cites an invalid recommendation.")

    return ValidatedSemanticResult(
        status=final_status,
        confidence_level=confidence_level,
        legacy_confidence=_legacy_confidence(confidence_level),
        evidence_ids=evidence_ids,
        explanation=output.explanation,
        recommendation_id=output.recommendation_id,
        provider=output.provider,
        model=output.model,
        prompt_template_version=output.prompt_template_version,
        kb_version=output.kb_version,
        items=items,
        confidence_basis=confidence_basis,
    )
