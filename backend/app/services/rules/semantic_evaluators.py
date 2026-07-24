"""Independent RAG-backed evaluators for RULE002, RULE004, and RULE008."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.domain import AcademicStatus
from app.models.analysis import Analysis
from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.topic import Topic
from app.services.ai.prompt_templates import PromptTemplate, get_prompt_template
from app.services.knowledge_base.reference_data import get_recommendations_for
from app.services.knowledge_base.runtime import SemanticRuntime
from app.services.knowledge_base.vector_store import RetrievedRecord
from app.services.rules.identifiers import (
    CLO_RELEVANCE,
    OUT_OF_SCOPE_CONTENT,
    QUESTION_FORMAT_SUITABILITY,
    RuleIdentifier,
)
from app.services.rules.question_hierarchy import scorable_leaves
from app.services.rules.references import find_cited_codes
from app.services.rules.semantic_governance import (
    SemanticRuleSpec,
    load_semantic_rule_spec,
)
from app.services.rules.semantic_types import SemanticValidationContext
from app.services.rules.semantic_validation import (
    SemanticOutputValidationError,
    semantic_output_schema,
    validate_semantic_output,
)


@dataclass(frozen=True)
class SemanticInputs:
    questions: tuple[Question, ...]
    evidence: tuple[Evidence, ...]
    clos: tuple[Clo, ...]
    topics: tuple[Topic, ...]
    assessment_records: tuple[AssessmentRecord, ...]


@dataclass(frozen=True)
class PreparedSemanticEvaluation:
    evidence: tuple[Evidence, ...]
    query_text: str
    allowed_evidence_types: frozenset[str]


@dataclass(frozen=True)
class SemanticRuleEvaluation:
    identifier: RuleIdentifier
    status: AcademicStatus
    confidence: float
    evidence_ids: list[uuid.UUID]
    explanation: str
    recommendation_id: str | None
    evaluator_type: str
    provider: str | None
    model: str | None
    prompt_template_version: str
    kb_version: str


def load_semantic_inputs(session: Session, analysis_id: uuid.UUID) -> SemanticInputs:
    return SemanticInputs(
        questions=tuple(
            session.execute(
                select(Question)
                .where(Question.analysis_id == analysis_id)
                .order_by(Question.sequence)
            )
            .scalars()
            .all()
        ),
        evidence=tuple(
            session.execute(
                select(Evidence)
                .where(Evidence.analysis_id == analysis_id)
                .order_by(Evidence.page_number, Evidence.created_at)
            )
            .scalars()
            .all()
        ),
        clos=tuple(
            session.execute(select(Clo).where(Clo.analysis_id == analysis_id)).scalars().all()
        ),
        topics=tuple(
            session.execute(select(Topic).where(Topic.analysis_id == analysis_id)).scalars().all()
        ),
        assessment_records=tuple(
            session.execute(
                select(AssessmentRecord).where(AssessmentRecord.analysis_id == analysis_id)
            )
            .scalars()
            .all()
        ),
    )


def _evidence_by_type(evidence: Sequence[Evidence], evidence_type: str) -> dict[str, Evidence]:
    return {item.item_reference: item for item in evidence if item.evidence_type == evidence_type}


def _missing_traces(inputs: SemanticInputs, *references: str) -> list[Evidence]:
    wanted = set(references)
    return [
        item
        for item in inputs.evidence
        if item.evidence_type in {"missing_section", "missing_semantic_input"}
        and item.item_reference in wanted
    ]


def _not_verified(
    identifier: RuleIdentifier,
    template: PromptTemplate,
    runtime: SemanticRuntime,
    explanation: str,
    evidence: Sequence[Evidence],
) -> SemanticRuleEvaluation:
    unique = list(dict.fromkeys(item.id for item in evidence))
    confidence = min((item.confidence for item in evidence), default=0.0)
    return SemanticRuleEvaluation(
        identifier=identifier,
        status=AcademicStatus.NOT_VERIFIED,
        confidence=confidence,
        evidence_ids=unique,
        explanation=explanation,
        recommendation_id=None,
        evaluator_type="semantic_precondition",
        provider=None,
        model=None,
        prompt_template_version=template.version,
        kb_version=runtime.snapshot.version,
    )


def _precondition_evidence(
    identifier: RuleIdentifier,
    inputs: SemanticInputs,
) -> list[Evidence]:
    traces = _missing_traces(
        inputs,
        "questions",
        "clos",
        "topics",
        "assessment_records",
    )
    if traces:
        return traces
    if identifier == OUT_OF_SCOPE_CONTENT:
        allowed_types = {"question_text", "topic"}
    elif identifier == QUESTION_FORMAT_SUITABILITY:
        allowed_types = {"question_text", "clo", "assessment_record"}
    else:
        allowed_types = {"question_text", "clo"}
    return [item for item in inputs.evidence if item.evidence_type in allowed_types]


def _prepare_clo_comparison(
    inputs: SemanticInputs,
    *,
    include_assessment: bool,
) -> PreparedSemanticEvaluation | str:
    leaves = scorable_leaves(inputs.questions)
    if not leaves:
        return "No readable scorable questions were extracted from the exam."
    if not inputs.clos:
        return "No usable CLO evidence was extracted from the TP-153."

    question_evidence = _evidence_by_type(inputs.evidence, "question_text")
    clo_evidence = _evidence_by_type(inputs.evidence, "clo")
    codes = [clo.code for clo in inputs.clos]
    selected: list[Evidence] = []
    cited_pairs: list[str] = []
    for question in leaves:
        cited = find_cited_codes(question.question_text, codes)
        if not cited:
            continue
        question_row = question_evidence.get(question.number_label)
        if question_row is not None:
            selected.append(question_row)
        for code in sorted(cited):
            clo_row = clo_evidence.get(code)
            if clo_row is not None:
                selected.append(clo_row)
                cited_pairs.append(f"{question.number_label}->{code}")

    if not cited_pairs:
        return (
            "No explicit question-to-CLO reference establishes which CLO evidence is intended; "
            "semantic relevance or format suitability cannot be verified safely."
        )
    if include_assessment:
        selected.extend(
            item for item in inputs.evidence if item.evidence_type == "assessment_record"
        )
    return PreparedSemanticEvaluation(
        evidence=tuple(dict.fromkeys(selected)),
        query_text=" ".join(
            [
                "question CLO relevance format suitability",
                *cited_pairs,
                *(item.extracted_text for item in selected),
            ]
        ),
        allowed_evidence_types=frozenset(
            {"question_text", "clo", "assessment_record"}
            if include_assessment
            else {"question_text", "clo"}
        ),
    )


def prepare_clo_relevance(inputs: SemanticInputs) -> PreparedSemanticEvaluation | str:
    return _prepare_clo_comparison(inputs, include_assessment=False)


def prepare_question_format_suitability(
    inputs: SemanticInputs,
) -> PreparedSemanticEvaluation | str:
    return _prepare_clo_comparison(inputs, include_assessment=True)


def prepare_out_of_scope_content(
    inputs: SemanticInputs,
) -> PreparedSemanticEvaluation | str:
    leaves = scorable_leaves(inputs.questions)
    if not leaves:
        return "No readable scorable questions were extracted from the exam."
    if not inputs.topics:
        return "No usable course-topic evidence was extracted from the TP-153."
    question_evidence = _evidence_by_type(inputs.evidence, "question_text")
    topic_evidence = [item for item in inputs.evidence if item.evidence_type == "topic"]
    selected = [
        question_evidence[question.number_label]
        for question in leaves
        if question.number_label in question_evidence
    ]
    selected.extend(topic_evidence)
    if not selected or not topic_evidence:
        return "Question and topic source evidence could not be assembled safely."
    return PreparedSemanticEvaluation(
        evidence=tuple(dict.fromkeys(selected)),
        query_text=" ".join(
            [
                "out of scope course topic assessed content",
                *(item.extracted_text for item in selected),
            ]
        ),
        allowed_evidence_types=frozenset({"question_text", "topic"}),
    )


def _retrieved_payload(records: Sequence[RetrievedRecord]) -> list[dict[str, object]]:
    return [
        {
            "official_id": record.official_id,
            "entity_type": record.entity_type,
            "text": record.text,
            "provenance_category": record.provenance_category,
            "kb_version": record.kb_version,
            "source_workbook": record.source_workbook,
            "source_row_number": record.source_row_number,
            "record_hash": record.record_hash,
        }
        for record in records
    ]


def _prompt_envelope(
    *,
    spec: SemanticRuleSpec,
    template: PromptTemplate,
    runtime: SemanticRuntime,
    prepared: PreparedSemanticEvaluation,
    retrieved: Sequence[RetrievedRecord],
    kb_source_dir: Path,
) -> str:
    recommendation_options: dict[str, list[dict[str, str]]] = {}
    for status in sorted(spec.allowed_statuses, key=lambda value: value.value):
        recommendation_options[status.value] = [
            {
                "recommendation_id": item.recommendation_id,
                "title": item.title,
                "text": item.text,
            }
            for item in get_recommendations_for(
                kb_source_dir.resolve(), spec.identifier.rule_id, status
            )
        ]
    payload = {
        "rule_id": spec.identifier.rule_id,
        "requirement_id": spec.identifier.requirement_id,
        "rule_name": spec.identifier.rule_name,
        "dimension": spec.dimension,
        "prompt_template_version": template.version,
        "kb_version": runtime.snapshot.version,
        "kb_hash": runtime.snapshot.aggregate_hash,
        "instruction": template.rule_instruction,
        "allowed_statuses": sorted(status.value for status in spec.allowed_statuses),
        "conditions": {
            "Satisfied": spec.satisfied_condition,
            "Partially Satisfied": spec.partially_satisfied_condition,
            "Not Satisfied": spec.not_satisfied_condition,
            "Not Verified": spec.not_verified_condition,
            "Not Applicable": spec.not_applicable_condition,
        },
        "controlled_recommendations": recommendation_options,
        "evidence": [
            {
                "id": str(item.id),
                "source_document": item.source_document.value,
                "evidence_type": item.evidence_type,
                "page_number": item.page_number,
                "item_reference": item.item_reference,
                "text": item.extracted_text,
                "confidence": item.confidence,
            }
            for item in prepared.evidence
        ],
        "retrieved_knowledge": _retrieved_payload(retrieved),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _rule_schema(
    spec: SemanticRuleSpec,
    template: PromptTemplate,
    runtime: SemanticRuntime,
) -> dict[str, object]:
    schema = semantic_output_schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    properties["rule_id"] = {"type": "string", "const": spec.identifier.rule_id}
    properties["requirement_id"] = {
        "type": "string",
        "const": spec.identifier.requirement_id,
    }
    properties["status"] = {
        "type": "string",
        "enum": sorted(status.value for status in spec.allowed_statuses),
    }
    properties["provider"] = {
        "type": "string",
        "const": runtime.provider.provider_name,
    }
    properties["model"] = {"type": "string", "const": runtime.provider.model_name}
    properties["prompt_template_version"] = {
        "type": "string",
        "const": template.version,
    }
    properties["kb_version"] = {
        "type": "string",
        "const": runtime.snapshot.version,
    }
    return schema


def _evaluate(
    *,
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    identifier: RuleIdentifier,
    inputs: SemanticInputs,
    prepare: Callable[[SemanticInputs], PreparedSemanticEvaluation | str],
    validation_retries: int,
) -> SemanticRuleEvaluation:
    template = get_prompt_template(identifier.rule_id)
    spec = load_semantic_rule_spec(kb_source_dir, identifier)
    prepared_or_reason = prepare(inputs)
    if isinstance(prepared_or_reason, str):
        return _not_verified(
            identifier,
            template,
            runtime,
            prepared_or_reason,
            _precondition_evidence(identifier, inputs),
        )
    prepared = prepared_or_reason

    retrieved = runtime.vector_store.query(
        prepared.query_text,
        kb_version=runtime.snapshot.version,
        dimension=spec.dimension,
        requirement_id=identifier.requirement_id,
        n_results=5,
    )
    if not retrieved:
        return _not_verified(
            identifier,
            template,
            runtime,
            "No relevant versioned knowledge-base context was retrieved, so the semantic "
            "conclusion cannot be verified safely.",
            prepared.evidence,
        )

    prompt = _prompt_envelope(
        spec=spec,
        template=template,
        runtime=runtime,
        prepared=prepared,
        retrieved=retrieved,
        kb_source_dir=kb_source_dir,
    )
    context = SemanticValidationContext(
        analysis_id=analysis.id,
        rule_spec=spec,
        prompt_template_version=template.version,
        kb_version=runtime.snapshot.version,
        allowed_evidence_ids=frozenset(item.id for item in prepared.evidence),
        allowed_evidence_types=prepared.allowed_evidence_types,
    )
    attempts = validation_retries + 1
    last_error: SemanticOutputValidationError | None = None
    for _ in range(attempts):
        raw = runtime.provider.generate_structured(
            system=template.system,
            prompt=prompt,
            schema=_rule_schema(spec, template, runtime),
        )
        try:
            result = validate_semantic_output(
                raw,
                session=session,
                context=context,
                provider=runtime.provider,
                kb_source_dir=kb_source_dir,
            )
            return SemanticRuleEvaluation(
                identifier=identifier,
                status=result.status,
                confidence=result.confidence,
                evidence_ids=result.evidence_ids,
                explanation=result.explanation,
                recommendation_id=result.recommendation_id,
                evaluator_type="semantic_ai",
                provider=result.provider,
                model=result.model,
                prompt_template_version=result.prompt_template_version,
                kb_version=result.kb_version,
            )
        except SemanticOutputValidationError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def evaluate_clo_relevance(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate(
        analysis=analysis,
        session=session,
        runtime=runtime,
        kb_source_dir=kb_source_dir,
        identifier=CLO_RELEVANCE,
        inputs=inputs,
        prepare=prepare_clo_relevance,
        validation_retries=validation_retries,
    )


def evaluate_question_format_suitability(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate(
        analysis=analysis,
        session=session,
        runtime=runtime,
        kb_source_dir=kb_source_dir,
        identifier=QUESTION_FORMAT_SUITABILITY,
        inputs=inputs,
        prepare=prepare_question_format_suitability,
        validation_retries=validation_retries,
    )


def evaluate_out_of_scope_content(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate(
        analysis=analysis,
        session=session,
        runtime=runtime,
        kb_source_dir=kb_source_dir,
        identifier=OUT_OF_SCOPE_CONTENT,
        inputs=inputs,
        prepare=prepare_out_of_scope_content,
        validation_retries=validation_retries,
    )


def evaluate_approved_semantic_rules(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    *,
    validation_retries: int,
) -> tuple[SemanticRuleEvaluation, ...]:
    inputs = load_semantic_inputs(session, analysis.id)
    return (
        evaluate_clo_relevance(
            analysis,
            session,
            runtime,
            kb_source_dir,
            inputs,
            validation_retries=validation_retries,
        ),
        evaluate_question_format_suitability(
            analysis,
            session,
            runtime,
            kb_source_dir,
            inputs,
            validation_retries=validation_retries,
        ),
        evaluate_out_of_scope_content(
            analysis,
            session,
            runtime,
            kb_source_dir,
            inputs,
            validation_retries=validation_retries,
        ),
    )
