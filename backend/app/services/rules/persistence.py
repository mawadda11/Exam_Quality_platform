from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.finding import Finding, FindingEvidence
from app.services.rules.identifiers import RuleIdentifier
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

    for evidence_id in dict.fromkeys(result.evidence_ids):
        session.add(FindingEvidence(finding_id=finding.id, evidence_id=evidence_id))
    session.flush()

    return finding
