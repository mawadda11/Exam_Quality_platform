from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.finding import Finding, FindingEvidence
from app.schemas.finding import FindingEvaluationDetails, FindingItemJudgmentDetails
from app.services.rules.identifiers import RuleIdentifier
from app.services.rules.semantic_evaluators import SemanticRuleEvaluation
from app.services.rules.types import RuleFindingResult

_EVALUATOR_TYPE = "deterministic_rule"


def persist_finding(
    session: Session,
    analysis_id: uuid.UUID,
    identifier: RuleIdentifier,
    result: RuleFindingResult,
) -> Finding:
    """Persists one finding for one rule execution, plus its finding_evidence
    trace links. Evidence ids are deduplicated (order-preserving) before
    linking, so a rule accidentally listing the same evidence row twice never
    produces duplicate finding_evidence rows."""
    existing = session.execute(
        select(Finding).where(
            Finding.analysis_id == analysis_id,
            Finding.rule_id == identifier.rule_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    evidence_ids = list(dict.fromkeys(result.evidence_ids))
    if evidence_ids:
        owned_ids = set(
            session.execute(
                select(Evidence.id).where(
                    Evidence.id.in_(evidence_ids),
                    Evidence.analysis_id == analysis_id,
                )
            ).scalars()
        )
        if owned_ids != set(evidence_ids):
            raise ValueError("Finding evidence must exist and belong to the same analysis.")

    finding = Finding(
        analysis_id=analysis_id,
        requirement_id=identifier.requirement_id,
        rule_id=identifier.rule_id,
        status=result.status,
        explanation=result.explanation,
        confidence=result.confidence,
        evaluator_type=_EVALUATOR_TYPE,
    )
    session.add(finding)
    session.flush()

    for evidence_id in evidence_ids:
        session.add(FindingEvidence(finding_id=finding.id, evidence_id=evidence_id))
    session.flush()

    return finding


def persist_semantic_finding(
    session: Session,
    analysis_id: uuid.UUID,
    evaluation: SemanticRuleEvaluation,
) -> Finding:
    """Persists a validated semantic result with trusted audit provenance."""
    existing = session.execute(
        select(Finding).where(
            Finding.analysis_id == analysis_id,
            Finding.rule_id == evaluation.identifier.rule_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    evidence_ids = list(dict.fromkeys(evaluation.evidence_ids))
    if not evidence_ids:
        raise ValueError("Semantic findings require at least one traceable evidence row.")
    if evidence_ids:
        owned_ids = set(
            session.execute(
                select(Evidence.id).where(
                    Evidence.id.in_(evidence_ids),
                    Evidence.analysis_id == analysis_id,
                )
            ).scalars()
        )
        if owned_ids != set(evidence_ids):
            raise ValueError(
                "Semantic finding evidence must exist and belong to the same analysis."
            )

    details = FindingEvaluationDetails(
        schema_version=1,
        decision=evaluation.status,
        evidence_used=evidence_ids,
        reasoning=evaluation.explanation,
        recommendation=evaluation.recommendation_id,
        confidence_basis=list(evaluation.confidence_basis),
        item_judgments=[
            FindingItemJudgmentDetails(
                source_evidence_id=item.source_evidence_id,
                target_evidence_ids=item.target_evidence_ids,
                status=item.status,
                reasoning=item.reasoning,
            )
            for item in evaluation.items
        ],
        retrieved_knowledge_ids=list(evaluation.retrieved_knowledge_ids),
    )
    finding = Finding(
        analysis_id=analysis_id,
        requirement_id=evaluation.identifier.requirement_id,
        rule_id=evaluation.identifier.rule_id,
        status=evaluation.status,
        explanation=evaluation.explanation,
        confidence=evaluation.confidence,
        confidence_level=evaluation.confidence_level,
        evaluation_details=details.model_dump(mode="json"),
        evaluator_type=evaluation.evaluator_type,
        recommendation_id=evaluation.recommendation_id,
        ai_provider=evaluation.provider,
        ai_model=evaluation.model,
        prompt_template_version=evaluation.prompt_template_version,
        kb_version=evaluation.kb_version,
    )
    session.add(finding)
    session.flush()
    for evidence_id in evidence_ids:
        session.add(FindingEvidence(finding_id=finding.id, evidence_id=evidence_id))
    session.flush()
    return finding
