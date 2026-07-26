"""Governed RAG-backed evaluators for the Version 1 semantic rule set."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.domain import AcademicStatus, SemanticConfidenceLevel
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
    ASSESSMENT_METHOD_CONSISTENCY,
    CLEAR_TASK_STATEMENT,
    CLO_RELEVANCE,
    COMPLETE_INSTRUCTIONS,
    COMPLETE_QUESTION_INFORMATION,
    OUT_OF_SCOPE_CONTENT,
    QUESTION_FORMAT_SUITABILITY,
    QUESTION_TO_CLO_MAPPING,
    QUESTION_TO_TOPIC_ALIGNMENT,
    UNAMBIGUOUS_WORDING,
    RuleIdentifier,
)
from app.services.rules.question_hierarchy import scorable_leaves
from app.services.rules.semantic_governance import SemanticRuleSpec, load_semantic_rule_spec
from app.services.rules.semantic_types import SemanticItemJudgment, SemanticValidationContext
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
    required_source_evidence_ids: frozenset[uuid.UUID]
    allowed_target_evidence_ids: frozenset[uuid.UUID]
    relationship_required: bool = False


@dataclass(frozen=True)
class SemanticRuleEvaluation:
    identifier: RuleIdentifier
    status: AcademicStatus
    confidence_level: SemanticConfidenceLevel
    confidence: float
    evidence_ids: list[uuid.UUID]
    explanation: str
    recommendation_id: str | None
    evaluator_type: str
    provider: str | None
    model: str | None
    prompt_template_version: str
    kb_version: str
    items: tuple[SemanticItemJudgment, ...] = ()
    confidence_basis: tuple[str, ...] = ()
    retrieved_knowledge_ids: tuple[str, ...] = ()


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


def _evidence_of_type(inputs: SemanticInputs, evidence_type: str) -> list[Evidence]:
    return [item for item in inputs.evidence if item.evidence_type == evidence_type]


def _question_evidence(inputs: SemanticInputs) -> list[Evidence]:
    leaves = scorable_leaves(inputs.questions)
    by_question_id = {
        item.question_id: item
        for item in inputs.evidence
        if item.evidence_type == "question_text" and item.question_id is not None
    }
    return [by_question_id[leaf.id] for leaf in leaves if leaf.id in by_question_id]


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
    return SemanticRuleEvaluation(
        identifier=identifier,
        status=AcademicStatus.NOT_VERIFIED,
        confidence_level=SemanticConfidenceLevel.LOW,
        confidence=0.0,
        evidence_ids=unique,
        explanation=explanation,
        recommendation_id=None,
        evaluator_type="semantic_precondition",
        provider=None,
        model=None,
        prompt_template_version=template.version,
        kb_version=runtime.snapshot.version,
        confidence_basis=("Required confirmed semantic evidence was unavailable.",),
    )


def _question_target_preparation(
    inputs: SemanticInputs,
    *,
    target_type: str,
    target_name: str,
    extra_context_types: frozenset[str] = frozenset(),
    relationship_required: bool = True,
) -> PreparedSemanticEvaluation | str:
    sources = _question_evidence(inputs)
    if not sources:
        return "No readable scorable question evidence was available from the confirmed exam."
    targets = _evidence_of_type(inputs, target_type)
    if not targets:
        return f"No usable {target_name} evidence was available from the confirmed TP-153."
    context = [item for item in inputs.evidence if item.evidence_type in extra_context_types]
    evidence = tuple(dict.fromkeys([*sources, *targets, *context]))
    return PreparedSemanticEvaluation(
        evidence=evidence,
        query_text=" ".join(item.extracted_text for item in evidence),
        allowed_evidence_types=frozenset({"question_text", target_type, *extra_context_types}),
        required_source_evidence_ids=frozenset(item.id for item in sources),
        allowed_target_evidence_ids=frozenset(item.id for item in [*targets, *context]),
        relationship_required=relationship_required,
    )


def prepare_question_to_clo_mapping(inputs: SemanticInputs) -> PreparedSemanticEvaluation | str:
    return _question_target_preparation(inputs, target_type="clo", target_name="CLO")


def prepare_clo_relevance(inputs: SemanticInputs) -> PreparedSemanticEvaluation | str:
    return _question_target_preparation(inputs, target_type="clo", target_name="CLO")


def prepare_question_format_suitability(
    inputs: SemanticInputs,
) -> PreparedSemanticEvaluation | str:
    return _question_target_preparation(
        inputs,
        target_type="clo",
        target_name="CLO",
        extra_context_types=frozenset({"assessment_record"}),
    )


def prepare_question_to_topic_alignment(
    inputs: SemanticInputs,
) -> PreparedSemanticEvaluation | str:
    return _question_target_preparation(inputs, target_type="topic", target_name="course-topic")


def prepare_out_of_scope_content(
    inputs: SemanticInputs,
) -> PreparedSemanticEvaluation | str:
    return _question_target_preparation(inputs, target_type="topic", target_name="course-topic")


def prepare_assessment_method_consistency(
    inputs: SemanticInputs,
) -> PreparedSemanticEvaluation | str:
    sources = _evidence_of_type(inputs, "exam_metadata")
    if not sources:
        return "The uploaded exam type could not be assembled as confirmed exam metadata evidence."
    targets = _evidence_of_type(inputs, "assessment_record")
    if not targets:
        return "No usable assessment-method or assessment-activity evidence was extracted."
    evidence = tuple(dict.fromkeys([*sources, *targets]))
    return PreparedSemanticEvaluation(
        evidence=evidence,
        query_text="assessment method consistency "
        + " ".join(item.extracted_text for item in evidence),
        allowed_evidence_types=frozenset({"exam_metadata", "assessment_record"}),
        required_source_evidence_ids=frozenset(item.id for item in sources),
        allowed_target_evidence_ids=frozenset(item.id for item in targets),
        relationship_required=True,
    )


def _question_text_preparation(
    inputs: SemanticInputs,
    *,
    include_instructions: bool = False,
) -> PreparedSemanticEvaluation | str:
    sources = _question_evidence(inputs)
    if not sources:
        return "No readable scorable question evidence was available from the confirmed exam."
    instructions = _evidence_of_type(inputs, "instructions") if include_instructions else []
    evidence = tuple(dict.fromkeys([*sources, *instructions]))
    return PreparedSemanticEvaluation(
        evidence=evidence,
        query_text=" ".join(item.extracted_text for item in evidence),
        allowed_evidence_types=frozenset(
            {"question_text", "instructions"} if include_instructions else {"question_text"}
        ),
        required_source_evidence_ids=frozenset(item.id for item in sources),
        allowed_target_evidence_ids=frozenset(item.id for item in instructions),
        relationship_required=False,
    )


def prepare_clear_task_statement(inputs: SemanticInputs) -> PreparedSemanticEvaluation | str:
    return _question_text_preparation(inputs)


def prepare_unambiguous_wording(inputs: SemanticInputs) -> PreparedSemanticEvaluation | str:
    return _question_text_preparation(inputs)


def prepare_complete_question_information(
    inputs: SemanticInputs,
) -> PreparedSemanticEvaluation | str:
    return _question_text_preparation(inputs, include_instructions=True)


def prepare_complete_instructions(inputs: SemanticInputs) -> PreparedSemanticEvaluation | str:
    return _question_text_preparation(inputs, include_instructions=True)


def _precondition_evidence(identifier: RuleIdentifier, inputs: SemanticInputs) -> list[Evidence]:
    references = ["questions"]
    if identifier in {
        QUESTION_TO_CLO_MAPPING,
        CLO_RELEVANCE,
        QUESTION_FORMAT_SUITABILITY,
    }:
        references.append("clos")
    if identifier in {QUESTION_TO_TOPIC_ALIGNMENT, OUT_OF_SCOPE_CONTENT}:
        references.append("topics")
    if identifier is ASSESSMENT_METHOD_CONSISTENCY:
        references.append("assessment_records")
    traces = _missing_traces(inputs, *references)
    if traces:
        return traces
    return list(inputs.evidence)


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
    source_ids = prepared.required_source_evidence_ids
    target_ids = prepared.allowed_target_evidence_ids
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
        "required_source_evidence_ids": sorted(str(item) for item in source_ids),
        "allowed_target_evidence_ids": sorted(str(item) for item in target_ids),
        "relationship_required": prepared.relationship_required,
        "item_contract": (
            "Return exactly one item per required source evidence ID. Cite only allowed target "
            "evidence IDs. Keep reasoning concise and evidence-to-rule focused."
        ),
        "evidence": [
            {
                "id": str(item.id),
                "role": (
                    "source"
                    if item.id in source_ids
                    else "target"
                    if item.id in target_ids
                    else "context"
                ),
                "source_document": item.source_document.value,
                "evidence_type": item.evidence_type,
                "page_number": item.page_number,
                "item_reference": item.item_reference,
                "text": item.extracted_text,
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

    retrieval_query = (
        f"{identifier.rule_id} {identifier.rule_name} {spec.dimension} {prepared.query_text}"
    )
    retrieved = runtime.vector_store.query(
        retrieval_query,
        kb_version=runtime.snapshot.version,
        dimension=spec.dimension,
        requirement_id=identifier.requirement_id,
        n_results=8,
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
        required_source_evidence_ids=prepared.required_source_evidence_ids,
        allowed_target_evidence_ids=prepared.allowed_target_evidence_ids,
        relationship_required=prepared.relationship_required,
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
            evaluator_type = (
                "local_semantic_baseline"
                if runtime.provider.provider_name == "local"
                else "semantic_ai"
            )
            return SemanticRuleEvaluation(
                identifier=identifier,
                status=result.status,
                confidence_level=result.confidence_level,
                confidence=result.legacy_confidence,
                evidence_ids=result.evidence_ids,
                explanation=result.explanation,
                recommendation_id=result.recommendation_id,
                evaluator_type=evaluator_type,
                provider=result.provider,
                model=result.model,
                prompt_template_version=result.prompt_template_version,
                kb_version=result.kb_version,
                items=result.items,
                confidence_basis=result.confidence_basis,
                retrieved_knowledge_ids=tuple(item.official_id for item in retrieved),
            )
        except SemanticOutputValidationError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def _evaluate_named(
    identifier: RuleIdentifier,
    prepare: Callable[[SemanticInputs], PreparedSemanticEvaluation | str],
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate(
        analysis=analysis,
        session=session,
        runtime=runtime,
        kb_source_dir=kb_source_dir,
        identifier=identifier,
        inputs=inputs,
        prepare=prepare,
        validation_retries=validation_retries,
    )


def evaluate_semantic_relationship_rules(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    *,
    validation_retries: int,
) -> tuple[SemanticRuleEvaluation, SemanticRuleEvaluation]:
    inputs = load_semantic_inputs(session, analysis.id)
    return (
        _evaluate_named(
            QUESTION_TO_CLO_MAPPING,
            prepare_question_to_clo_mapping,
            analysis,
            session,
            runtime,
            kb_source_dir,
            inputs,
            validation_retries,
        ),
        _evaluate_named(
            QUESTION_TO_TOPIC_ALIGNMENT,
            prepare_question_to_topic_alignment,
            analysis,
            session,
            runtime,
            kb_source_dir,
            inputs,
            validation_retries,
        ),
    )


def evaluate_semantic_judgment_rules(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    *,
    validation_retries: int,
) -> tuple[SemanticRuleEvaluation, ...]:
    inputs = load_semantic_inputs(session, analysis.id)
    definitions = (
        (CLO_RELEVANCE, prepare_clo_relevance),
        (ASSESSMENT_METHOD_CONSISTENCY, prepare_assessment_method_consistency),
        (QUESTION_FORMAT_SUITABILITY, prepare_question_format_suitability),
        (OUT_OF_SCOPE_CONTENT, prepare_out_of_scope_content),
        (CLEAR_TASK_STATEMENT, prepare_clear_task_statement),
        (UNAMBIGUOUS_WORDING, prepare_unambiguous_wording),
        (COMPLETE_QUESTION_INFORMATION, prepare_complete_question_information),
        (COMPLETE_INSTRUCTIONS, prepare_complete_instructions),
    )
    return tuple(
        _evaluate_named(
            identifier,
            prepare,
            analysis,
            session,
            runtime,
            kb_source_dir,
            inputs,
            validation_retries,
        )
        for identifier, prepare in definitions
    )


def evaluate_approved_semantic_rules(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    *,
    validation_retries: int,
) -> tuple[SemanticRuleEvaluation, ...]:
    """Compatibility wrapper returning the complete M6-M9 semantic scope."""

    relationships = evaluate_semantic_relationship_rules(
        analysis,
        session,
        runtime,
        kb_source_dir,
        validation_retries=validation_retries,
    )
    judgments = evaluate_semantic_judgment_rules(
        analysis,
        session,
        runtime,
        kb_source_dir,
        validation_retries=validation_retries,
    )
    return (*relationships, *judgments)


# Public one-rule wrappers retained for focused tests and provider integrations.
def evaluate_question_to_clo_mapping(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate_named(
        QUESTION_TO_CLO_MAPPING,
        prepare_question_to_clo_mapping,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
    )


def evaluate_clo_relevance(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate_named(
        CLO_RELEVANCE,
        prepare_clo_relevance,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
    )


def evaluate_assessment_method_consistency(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate_named(
        ASSESSMENT_METHOD_CONSISTENCY,
        prepare_assessment_method_consistency,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
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
    return _evaluate_named(
        QUESTION_FORMAT_SUITABILITY,
        prepare_question_format_suitability,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
    )


def evaluate_question_to_topic_alignment(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate_named(
        QUESTION_TO_TOPIC_ALIGNMENT,
        prepare_question_to_topic_alignment,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
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
    return _evaluate_named(
        OUT_OF_SCOPE_CONTENT,
        prepare_out_of_scope_content,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
    )


def evaluate_clear_task_statement(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate_named(
        CLEAR_TASK_STATEMENT,
        prepare_clear_task_statement,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
    )


def evaluate_unambiguous_wording(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate_named(
        UNAMBIGUOUS_WORDING,
        prepare_unambiguous_wording,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
    )


def evaluate_complete_question_information(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate_named(
        COMPLETE_QUESTION_INFORMATION,
        prepare_complete_question_information,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
    )


def evaluate_complete_instructions(
    analysis: Analysis,
    session: Session,
    runtime: SemanticRuntime,
    kb_source_dir: Path,
    inputs: SemanticInputs,
    *,
    validation_retries: int,
) -> SemanticRuleEvaluation:
    return _evaluate_named(
        COMPLETE_INSTRUCTIONS,
        prepare_complete_instructions,
        analysis,
        session,
        runtime,
        kb_source_dir,
        inputs,
        validation_retries,
    )
