"""Deterministic validation gate for untrusted semantic model output."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.domain import UploadedFileType
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
    SemanticValidationContext,
    ValidatedSemanticResult,
)


class SemanticOutputValidationError(RuntimeError):
    """Invalid model output is never released as an academic finding."""


def semantic_output_schema() -> dict[str, object]:
    return SemanticAiOutput.model_json_schema()


def _validate_extraction_provenance(
    evidence_rows: list[Evidence],
    *,
    session: Session,
    context: SemanticValidationContext,
) -> None:
    """Cross-check semantic citations against their extracted domain rows."""
    for evidence in evidence_rows:
        if evidence.evidence_type == "question_text":
            if evidence.source_document is not UploadedFileType.EXAM:
                raise SemanticOutputValidationError(
                    "Question evidence does not originate from the exam."
                )
            exists = session.execute(
                select(Question.id).where(
                    Question.analysis_id == context.analysis_id,
                    Question.number_label == evidence.item_reference,
                    Question.question_text == evidence.extracted_text,
                    Question.page_number == evidence.page_number,
                )
            ).first()
            if exists is None:
                raise SemanticOutputValidationError(
                    "Question evidence has no matching extracted question."
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
                raise SemanticOutputValidationError("CLO evidence has no matching extracted CLO.")
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
                    "Topic evidence has no matching extracted topic."
                )
        elif (
            evidence.evidence_type == "assessment_record"
            and evidence.source_document is not UploadedFileType.TP153
        ):
            raise SemanticOutputValidationError(
                "Assessment evidence does not originate from the TP-153."
            )


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
    if output.status not in spec.allowed_statuses:
        raise SemanticOutputValidationError(
            "Provider output contains a status not allowed for this rule."
        )
    if output.provider != provider.provider_name or output.model != provider.model_name:
        raise SemanticOutputValidationError("Provider/model provenance does not match the adapter.")
    if output.prompt_template_version != context.prompt_template_version:
        raise SemanticOutputValidationError("Prompt-template version does not match.")
    if output.kb_version != context.kb_version:
        raise SemanticOutputValidationError("Knowledge-base version does not match.")

    output_ids = set(output.evidence_ids)
    if not output_ids:
        raise SemanticOutputValidationError("Semantic findings require at least one evidence ID.")
    if not output_ids.issubset(context.allowed_evidence_ids):
        raise SemanticOutputValidationError("Provider output cites evidence outside its context.")

    evidence_rows = list(
        session.execute(select(Evidence).where(Evidence.id.in_(output_ids))).scalars().all()
    )
    if len(evidence_rows) != len(output_ids):
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

    eligible = {
        item.recommendation_id
        for item in get_recommendations_for(
            kb_source_dir.resolve(), spec.identifier.rule_id, output.status
        )
    }
    if eligible:
        if output.recommendation_id not in eligible:
            raise SemanticOutputValidationError(
                "Provider output does not cite an applicable controlled recommendation."
            )
    elif output.recommendation_id is not None:
        raise SemanticOutputValidationError(
            "Provider output cites a recommendation that does not apply to this status."
        )
    if output.recommendation_id is not None:
        recommendation = get_recommendation_by_id(kb_source_dir.resolve(), output.recommendation_id)
        if recommendation is None or recommendation.rule_id != spec.identifier.rule_id:
            raise SemanticOutputValidationError("Provider output cites an invalid recommendation.")

    return ValidatedSemanticResult(
        status=output.status,
        confidence=output.confidence,
        evidence_ids=output.evidence_ids,
        explanation=output.explanation,
        recommendation_id=output.recommendation_id,
        provider=output.provider,
        model=output.model,
        prompt_template_version=output.prompt_template_version,
        kb_version=output.kb_version,
    )
