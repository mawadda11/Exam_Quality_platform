"""Pure report-content assembly: turns an analysis's already-persisted,
immutable Findings into a single frozen ReportContent snapshot, ready for
PDF rendering. Reuses the exact M9 read-time logic (calculate_overall_score,
count_statuses, get_requirement_display, get_recommendations_for) rather
than recomputing scoring or KB lookups a second way - this module only
adds the "freeze it into one structure, once, for this generation" step
M10 needs on top of what M9 already built.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app.core.domain import AcademicStatus, ExamType, UploadedFileType
from app.models.analysis import Analysis
from app.models.finding import Finding
from app.services.knowledge_base.manifest import KB_VERSION
from app.services.knowledge_base.reference_data import (
    RecommendationDisplay,
    get_recommendations_for,
    get_requirement_display,
)
from app.services.rules.scoring import calculate_overall_score, count_statuses


@dataclass(frozen=True)
class EvidenceCitation:
    source_document: UploadedFileType
    evidence_type: str
    page_number: int
    item_reference: str


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

    @property
    def missing_evidence(self) -> tuple[ReportFindingEntry, ...]:
        # SCORING_POLICY.md: Not Verified results must remain visible even
        # though excluded from the denominator - called out separately here
        # exactly as the M9 UI does, using each finding's own explanation.
        return tuple(f for f in self.findings if f.status is AcademicStatus.NOT_VERIFIED)


def _build_finding_entry(finding: Finding, source_dir: Path) -> ReportFindingEntry:
    display = get_requirement_display(source_dir, finding.requirement_id)
    recommendations = get_recommendations_for(source_dir, finding.rule_id, finding.status)
    evidence = tuple(
        EvidenceCitation(
            source_document=link.evidence.source_document,
            evidence_type=link.evidence.evidence_type,
            page_number=link.evidence.page_number,
            item_reference=link.evidence.item_reference,
        )
        for link in finding.evidence_links
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
        evidence=evidence,
        recommendations=recommendations,
    )


def assemble_report_content(
    analysis: Analysis,
    findings: Sequence[Finding],
    kb_source_dir: Path,
    generated_at: datetime,
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
    )
