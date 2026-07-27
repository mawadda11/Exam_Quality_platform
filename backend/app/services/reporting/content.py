"""Pure, governed report-content assembly.

The report freezes already-persisted findings and source records into one
immutable presentation snapshot. Scoring, requirement metadata,
recommendations, semantic confidence, item judgments, and runtime capability
coverage are reused from the same authoritative backend contracts exposed by
the API; this module never invents academic facts or recalculates semantic
relationships independently.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.core.domain import (
    AcademicStatus,
    ExamType,
    SemanticConfidenceLevel,
    UploadedFileType,
)
from app.models.analysis import Analysis
from app.models.assessment_record import AssessmentRecord
from app.models.finding import Finding
from app.schemas.finding import FindingEvaluationDetails
from app.schemas.rule_coverage import RuleCoverageAuditResponse
from app.services.knowledge_base.manifest import KB_VERSION
from app.services.knowledge_base.reference_data import (
    RecommendationDisplay,
    get_controlled_recommendations,
    get_requirement_display,
)
from app.services.rules.scoring import calculate_overall_score, count_statuses


@dataclass(frozen=True)
class EvidenceCitation:
    source_document: UploadedFileType
    evidence_type: str
    page_number: int
    item_reference: str
    id: uuid.UUID | None = None


@dataclass(frozen=True)
class ReportItemJudgment:
    source_evidence_id: uuid.UUID
    source_evidence: EvidenceCitation | None
    target_evidence_ids: tuple[uuid.UUID, ...]
    target_evidence: tuple[EvidenceCitation, ...]
    unresolved_target_evidence_ids: tuple[uuid.UUID, ...]
    status: AcademicStatus
    reasoning: str

    @property
    def is_derived_relationship(self) -> bool:
        return bool(self.target_evidence_ids)


@dataclass(frozen=True)
class ReportAssessmentRecordEntry:
    method: str
    activity: str | None
    percentage: float | None
    page_number: int


@dataclass(frozen=True)
class ReportFindingEntry:
    requirement_id: str
    rule_id: str
    requirement_name: str
    dimension: str
    source_type: str
    officiality: str
    status: AcademicStatus
    explanation: str
    evidence: tuple[EvidenceCitation, ...]
    recommendations: tuple[RecommendationDisplay, ...]
    evaluator_type: str = "deterministic_rule"
    confidence_level: SemanticConfidenceLevel | None = None
    evaluation_reasoning: str | None = None
    confidence_basis: tuple[str, ...] = ()
    item_judgments: tuple[ReportItemJudgment, ...] = ()
    retrieved_knowledge_ids: tuple[str, ...] = ()
    ai_provider: str | None = None
    ai_model: str | None = None
    prompt_template_version: str | None = None
    finding_kb_version: str | None = None

    @property
    def contains_derived_relationships(self) -> bool:
        return self.rule_id in {"RULE001", "RULE007"} and any(
            item.is_derived_relationship for item in self.item_judgments
        )


@dataclass(frozen=True)
class ReportContent:
    analysis_id: uuid.UUID
    course_code: str
    course_name: str
    exam_type: ExamType
    term: str
    kb_version: str
    generated_at: datetime
    score: Decimal | None
    score_label: str | None
    denominator: int
    satisfied_count: int
    partially_satisfied_count: int
    not_satisfied_count: int
    not_verified_count: int
    not_applicable_count: int
    findings: tuple[ReportFindingEntry, ...]
    assessment_records: tuple[ReportAssessmentRecordEntry, ...] = ()
    rule_coverage: RuleCoverageAuditResponse | None = None

    @property
    def missing_evidence(self) -> tuple[ReportFindingEntry, ...]:
        # Not Verified remains visible but is excluded from the denominator.
        return tuple(f for f in self.findings if f.status is AcademicStatus.NOT_VERIFIED)

    @property
    def earned_credit(self) -> Decimal:
        return Decimal(self.satisfied_count) + (
            Decimal(self.partially_satisfied_count) * Decimal("0.5")
        )


def _citation_from_linked_evidence(finding: Finding) -> tuple[EvidenceCitation, ...]:
    return tuple(
        EvidenceCitation(
            id=link.evidence.id,
            source_document=link.evidence.source_document,
            evidence_type=link.evidence.evidence_type,
            page_number=link.evidence.page_number,
            item_reference=link.evidence.item_reference,
        )
        for link in finding.evidence_links
    )


def _build_item_judgments(
    details: FindingEvaluationDetails | None,
    citations: tuple[EvidenceCitation, ...],
) -> tuple[ReportItemJudgment, ...]:
    if details is None:
        return ()

    citations_by_id = {citation.id: citation for citation in citations if citation.id is not None}
    result: list[ReportItemJudgment] = []
    for item in details.item_judgments:
        target_ids = tuple(item.target_evidence_ids)
        resolved_targets = tuple(
            citations_by_id[target_id] for target_id in target_ids if target_id in citations_by_id
        )
        unresolved_targets = tuple(
            target_id for target_id in target_ids if target_id not in citations_by_id
        )
        result.append(
            ReportItemJudgment(
                source_evidence_id=item.source_evidence_id,
                source_evidence=citations_by_id.get(item.source_evidence_id),
                target_evidence_ids=target_ids,
                target_evidence=resolved_targets,
                unresolved_target_evidence_ids=unresolved_targets,
                status=item.status,
                reasoning=item.reasoning,
            )
        )
    return tuple(result)


def _build_finding_entry(finding: Finding, source_dir: Path) -> ReportFindingEntry:
    display = get_requirement_display(source_dir, finding.requirement_id)
    recommendations = get_controlled_recommendations(
        source_dir,
        finding.rule_id,
        finding.status,
        finding.recommendation_id,
    )
    citations = _citation_from_linked_evidence(finding)
    details = (
        FindingEvaluationDetails.model_validate(finding.evaluation_details, strict=False)
        if finding.evaluation_details is not None
        else None
    )
    return ReportFindingEntry(
        requirement_id=finding.requirement_id,
        rule_id=finding.rule_id,
        requirement_name=display.requirement_name,
        dimension=display.dimension,
        source_type=display.source_type,
        officiality=display.officiality,
        status=finding.status,
        explanation=finding.explanation,
        evidence=citations,
        recommendations=recommendations,
        evaluator_type=finding.evaluator_type,
        confidence_level=finding.confidence_level,
        evaluation_reasoning=details.reasoning if details is not None else None,
        confidence_basis=tuple(details.confidence_basis) if details is not None else (),
        item_judgments=_build_item_judgments(details, citations),
        retrieved_knowledge_ids=(
            tuple(details.retrieved_knowledge_ids) if details is not None else ()
        ),
        ai_provider=finding.ai_provider,
        ai_model=finding.ai_model,
        prompt_template_version=finding.prompt_template_version,
        finding_kb_version=finding.kb_version,
    )


def _assessment_entry(record: AssessmentRecord) -> ReportAssessmentRecordEntry:
    return ReportAssessmentRecordEntry(
        method=record.method,
        activity=record.activity,
        percentage=record.percentage,
        page_number=record.page_number,
    )


def assemble_report_content(
    analysis: Analysis,
    findings: Sequence[Finding],
    kb_source_dir: Path,
    generated_at: datetime,
    *,
    assessment_records: Sequence[AssessmentRecord] = (),
    rule_coverage: RuleCoverageAuditResponse | None = None,
) -> ReportContent:
    statuses = [f.status for f in findings]
    score_result = calculate_overall_score(statuses)
    counts = count_statuses(statuses)
    entries = tuple(_build_finding_entry(f, kb_source_dir) for f in findings)

    return ReportContent(
        analysis_id=analysis.id,
        course_code=analysis.course.code,
        course_name=analysis.course.name,
        exam_type=analysis.exam_type,
        term=analysis.term,
        kb_version=KB_VERSION,
        generated_at=generated_at,
        score=score_result.score,
        score_label=score_result.label,
        denominator=score_result.denominator,
        satisfied_count=counts[AcademicStatus.SATISFIED],
        partially_satisfied_count=counts[AcademicStatus.PARTIALLY_SATISFIED],
        not_satisfied_count=counts[AcademicStatus.NOT_SATISFIED],
        not_verified_count=counts[AcademicStatus.NOT_VERIFIED],
        not_applicable_count=counts[AcademicStatus.NOT_APPLICABLE],
        findings=entries,
        assessment_records=tuple(_assessment_entry(item) for item in assessment_records),
        rule_coverage=rule_coverage,
    )
