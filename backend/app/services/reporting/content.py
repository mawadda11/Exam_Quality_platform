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
from collections import defaultdict
from collections.abc import Mapping, Sequence
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
from app.models.clo import Clo
from app.models.document_reference import DocumentReference
from app.models.finding import Finding
from app.models.question import Question
from app.models.supporting_material import SupportingMaterial
from app.models.supporting_material_annotation import SupportingMaterialAnnotation
from app.models.topic import Topic
from app.schemas.finding import FindingEvaluationDetails
from app.schemas.rule_coverage import RuleCoverageAuditResponse
from app.services.extraction.line_classification import parse_declared_total
from app.services.knowledge_base.manifest import KB_VERSION
from app.services.knowledge_base.reference_data import (
    RecommendationDisplay,
    get_controlled_recommendations,
    get_requirement_display,
)
from app.services.rules.question_hierarchy import scorable_leaves
from app.services.rules.scoring import calculate_overall_score, count_statuses
from app.services.rules.versioning import (
    LEGACY_CAPABILITY_VERSION,
    effective_capability_version,
)


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
class ReportSupportingMaterialEntry:
    identifier: uuid.UUID
    material_type: str
    page_number: int
    source_text: str
    confidence: float
    extraction_method: str


@dataclass(frozen=True)
class ReportSupportingAnnotationEntry:
    annotation_type: str
    original_text: str
    page_number: int
    confidence: float


@dataclass(frozen=True)
class ReportDocumentReferenceEntry:
    original_text: str
    target_type: str
    target_label: str
    page_number: int
    confidence: float
    resolution_status: str
    candidate_count: int


@dataclass(frozen=True)
class ReportRelationshipEntry:
    """One CLO or topic row for the report's CLO/Topic Analysis tables.

    Mirrors the same worst-status-wins rollup and Satisfied/Partially
    Satisfied marks criterion already used by the frontend Alignment &
    Coverage page, computed here from the same governed RULE001/RULE007
    item judgments rather than recalculated independently.
    """

    identifier: str
    text: str
    linked_question_labels: tuple[str, ...]
    total_marks: float
    coverage_status: AcademicStatus
    # True when `identifier` had to fall back to the full source text because
    # no short code was available (e.g. an uncoded course topic) - the report
    # renderer applies the report-language display rule only in that case,
    # never to a genuine short code such as "CLO1".
    identifier_is_source_text: bool = False


@dataclass(frozen=True)
class ReportExamSummary:
    scorable_question_count: int
    declared_total_marks: float | None
    calculated_total_marks: float | None
    supporting_material_count: int
    missing_or_ambiguous_reference_count: int


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
    supporting_materials: tuple[ReportSupportingMaterialEntry, ...] = ()
    supporting_annotations: tuple[ReportSupportingAnnotationEntry, ...] = ()
    document_references: tuple[ReportDocumentReferenceEntry, ...] = ()
    capability_version: str = LEGACY_CAPABILITY_VERSION
    clo_entries: tuple[ReportRelationshipEntry, ...] = ()
    topic_entries: tuple[ReportRelationshipEntry, ...] = ()
    exam_summary: ReportExamSummary | None = None

    @property
    def missing_evidence(self) -> tuple[ReportFindingEntry, ...]:
        # Not Verified remains visible but is excluded from the denominator.
        return tuple(f for f in self.findings if f.status is AcademicStatus.NOT_VERIFIED)

    @property
    def strengths(self) -> tuple[ReportFindingEntry, ...]:
        return tuple(f for f in self.findings if f.status is AcademicStatus.SATISFIED)

    @property
    def areas_for_improvement(self) -> tuple[ReportFindingEntry, ...]:
        attention = {AcademicStatus.PARTIALLY_SATISFIED, AcademicStatus.NOT_SATISFIED}
        return tuple(f for f in self.findings if f.status in attention)

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


def _supporting_material_entry(record: SupportingMaterial) -> ReportSupportingMaterialEntry:
    return ReportSupportingMaterialEntry(
        identifier=record.id,
        material_type=record.material_type.value,
        page_number=record.page_number,
        source_text=record.source_text,
        confidence=record.confidence,
        extraction_method=record.extraction_method,
    )


def _supporting_annotation_entry(
    record: SupportingMaterialAnnotation,
    presentation_text: str | None = None,
) -> ReportSupportingAnnotationEntry:
    return ReportSupportingAnnotationEntry(
        annotation_type=record.annotation_type.value,
        original_text=presentation_text or record.original_text,
        page_number=record.page_number,
        confidence=record.confidence,
    )


def _document_reference_entry(
    record: DocumentReference,
    confirmed_review_id: uuid.UUID | None,
) -> ReportDocumentReferenceEntry:
    candidates = [
        item
        for item in record.association_candidates
        if item.review_revision_id == confirmed_review_id
    ]
    exact = [item for item in candidates if item.exact_label_match]
    selected = [item for item in exact if item.selected]
    resolution = (
        "resolved" if len(selected) == 1 else ("ambiguous" if len(exact) > 1 else "unresolved")
    )
    return ReportDocumentReferenceEntry(
        original_text=record.original_text,
        target_type=record.target_type.value,
        target_label=record.target_label,
        page_number=record.page_number,
        confidence=record.confidence,
        resolution_status=resolution,
        candidate_count=len(candidates),
    )


# Best-to-worst is deliberately the reverse of scoring precedence: a single
# Satisfied relationship is enough to call a CLO/topic covered, matching the
# same worst-status-wins-only-when-nothing-better-exists rollup already used
# by the frontend Alignment & Coverage page's coverageStatus().
_COVERAGE_STATUS_BEST_FIRST = (
    AcademicStatus.SATISFIED,
    AcademicStatus.PARTIALLY_SATISFIED,
    AcademicStatus.NOT_VERIFIED,
    AcademicStatus.NOT_APPLICABLE,
)
_MARKS_CONTRIBUTING_STATUSES = {AcademicStatus.SATISFIED, AcademicStatus.PARTIALLY_SATISFIED}


def _coverage_status(statuses: Sequence[AcademicStatus]) -> AcademicStatus:
    for candidate in _COVERAGE_STATUS_BEST_FIRST:
        if candidate in statuses:
            return candidate
    return AcademicStatus.NOT_SATISFIED


def _relationship_entries(
    records: Sequence[tuple[str, str, bool]],
    questions: Sequence[Question],
    findings: Sequence[Finding],
    *,
    rule_id: str,
    target_evidence_type: str,
) -> tuple[ReportRelationshipEntry, ...]:
    marks_by_label = {q.number_label: (q.marks or 0.0) for q in scorable_leaves(questions)}
    sequence_by_label = {q.number_label: q.sequence for q in questions}
    matches: dict[str, list[tuple[str, AcademicStatus]]] = defaultdict(list)

    for finding in findings:
        if finding.rule_id != rule_id or finding.evaluation_details is None:
            continue
        details = FindingEvaluationDetails.model_validate(finding.evaluation_details, strict=False)
        evidence_by_id = {link.evidence.id: link.evidence for link in finding.evidence_links}
        for judgment in details.item_judgments:
            source = evidence_by_id.get(judgment.source_evidence_id)
            if source is None or source.evidence_type != "question_text":
                continue
            for target_id in judgment.target_evidence_ids:
                target = evidence_by_id.get(target_id)
                if target is None or target.evidence_type != target_evidence_type:
                    continue
                matches[target.item_reference].append((source.item_reference, judgment.status))

    entries: list[ReportRelationshipEntry] = []
    for identifier, text, identifier_is_source_text in records:
        pairs = matches.get(identifier, [])
        linked_labels = sorted(
            dict.fromkeys(label for label, _ in pairs),
            key=lambda label: sequence_by_label.get(label, len(sequence_by_label)),
        )
        supported_labels = {
            label for label, status in pairs if status in _MARKS_CONTRIBUTING_STATUSES
        }
        total_marks = sum(marks_by_label.get(label, 0.0) for label in supported_labels)
        coverage_status = (
            _coverage_status([status for _, status in pairs])
            if pairs
            else AcademicStatus.NOT_SATISFIED
        )
        entries.append(
            ReportRelationshipEntry(
                identifier=identifier,
                text=text,
                linked_question_labels=tuple(linked_labels),
                total_marks=total_marks,
                coverage_status=coverage_status,
                identifier_is_source_text=identifier_is_source_text,
            )
        )
    return tuple(entries)


def _marks_totals_from_findings(
    findings: Sequence[Finding],
    questions: Sequence[Question],
) -> tuple[float | None, float | None]:
    """Declared total is parsed from the RULE018 finding's own linked
    declared-total evidence text; calculated total is the sum of scorable
    leaf marks. This mirrors RULE018's own arithmetic exactly (see
    app.services.rules.marks_total.evaluate_marks_and_total) so the Exam
    Summary always agrees with the Marks & Structure narrative for the same
    finding, instead of independently recomputing or misreading evidence
    fields.
    """
    marks_finding = next((f for f in findings if f.rule_id == "RULE018"), None)
    if marks_finding is None:
        return None, None
    declared_total_evidence = next(
        (
            link.evidence
            for link in marks_finding.evidence_links
            if link.evidence.evidence_type == "declared_total"
        ),
        None,
    )
    declared = (
        None
        if declared_total_evidence is None
        else parse_declared_total(declared_total_evidence.extracted_text)
    )
    leaves = scorable_leaves(questions)
    calculated = (
        None
        if not leaves or any(leaf.marks is None for leaf in leaves)
        else float(sum((Decimal(str(leaf.marks)) for leaf in leaves), start=Decimal("0")))
    )
    return declared, calculated


def _build_exam_summary(
    questions: Sequence[Question],
    findings: Sequence[Finding],
    supporting_materials: Sequence[SupportingMaterial],
    document_references: Sequence[ReportDocumentReferenceEntry],
) -> ReportExamSummary:
    declared, calculated = _marks_totals_from_findings(findings, questions)
    return ReportExamSummary(
        scorable_question_count=len(scorable_leaves(questions)),
        declared_total_marks=declared,
        calculated_total_marks=calculated,
        supporting_material_count=len(supporting_materials),
        missing_or_ambiguous_reference_count=sum(
            1
            for reference in document_references
            if reference.resolution_status in {"ambiguous", "unresolved"}
        ),
    )


def assemble_report_content(
    analysis: Analysis,
    findings: Sequence[Finding],
    kb_source_dir: Path,
    generated_at: datetime,
    *,
    assessment_records: Sequence[AssessmentRecord] = (),
    rule_coverage: RuleCoverageAuditResponse | None = None,
    supporting_materials: Sequence[SupportingMaterial] = (),
    supporting_annotations: Sequence[SupportingMaterialAnnotation] = (),
    supporting_annotation_texts: Mapping[uuid.UUID, str] | None = None,
    document_references: Sequence[DocumentReference] = (),
    questions: Sequence[Question] = (),
    clos: Sequence[Clo] = (),
    topics: Sequence[Topic] = (),
) -> ReportContent:
    statuses = [f.status for f in findings]
    score_result = calculate_overall_score(statuses)
    counts = count_statuses(statuses)
    entries = tuple(_build_finding_entry(f, kb_source_dir) for f in findings)
    document_reference_entries = tuple(
        _document_reference_entry(item, analysis.confirmed_review_id)
        for item in document_references
    )
    clo_entries = _relationship_entries(
        [(clo.code, clo.text, False) for clo in clos],
        questions,
        findings,
        rule_id="RULE001",
        target_evidence_type="clo",
    )
    topic_entries = _relationship_entries(
        [(topic.code or topic.text, topic.text, topic.code is None) for topic in topics],
        questions,
        findings,
        rule_id="RULE007",
        target_evidence_type="topic",
    )
    exam_summary = _build_exam_summary(
        questions, findings, supporting_materials, document_reference_entries
    )

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
        supporting_materials=tuple(
            _supporting_material_entry(item) for item in supporting_materials
        ),
        supporting_annotations=tuple(
            _supporting_annotation_entry(
                item,
                (supporting_annotation_texts or {}).get(item.id),
            )
            for item in supporting_annotations
        ),
        document_references=document_reference_entries,
        capability_version=effective_capability_version(analysis),
        clo_entries=clo_entries,
        topic_entries=topic_entries,
        exam_summary=exam_summary,
    )
