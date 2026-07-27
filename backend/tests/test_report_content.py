from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.core.domain import AcademicStatus, ExamType, UploadedFileType
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.evidence import Evidence
from app.models.finding import Finding, FindingEvidence
from app.services.knowledge_base.manifest import KB_VERSION
from app.services.reporting.content import assemble_report_content

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_SOURCE = REPO_ROOT / "knowledge_base" / "source"
GENERATED_AT = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


def _analysis() -> Analysis:
    analysis = Analysis(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        course_id=uuid.uuid4(),
        exam_type=ExamType.MIDTERM,
        term="2026 Spring",
    )
    analysis.course = Course(code="CPIT-450", name="Software Engineering")
    return analysis


def _finding(
    analysis_id: uuid.UUID,
    requirement_id: str,
    rule_id: str,
    status: AcademicStatus,
    evidence: list[Evidence] | None = None,
) -> Finding:
    finding = Finding(
        id=uuid.uuid4(),
        analysis_id=analysis_id,
        requirement_id=requirement_id,
        rule_id=rule_id,
        status=status,
        explanation="test explanation",
        confidence=1.0,
        evaluator_type="deterministic_rule",
    )
    finding.evidence_links = [
        FindingEvidence(finding_id=finding.id, evidence_id=ev.id, evidence=ev)
        for ev in (evidence or [])
    ]
    return finding


def test_assemble_report_content_computes_score_and_counts_from_findings() -> None:
    analysis = _analysis()
    findings = [
        _finding(analysis.id, "REQ001", "RULE001", AcademicStatus.SATISFIED),
        _finding(analysis.id, "REQ005", "RULE005", AcademicStatus.PARTIALLY_SATISFIED),
        _finding(analysis.id, "REQ007", "RULE007", AcademicStatus.NOT_SATISFIED),
        _finding(analysis.id, "REQ009", "RULE009", AcademicStatus.NOT_VERIFIED),
        _finding(analysis.id, "REQ018", "RULE018", AcademicStatus.NOT_APPLICABLE),
    ]

    content = assemble_report_content(analysis, findings, KB_SOURCE, GENERATED_AT)

    assert content.analysis_id == analysis.id
    assert content.course_code == "CPIT-450"
    assert content.course_name == "Software Engineering"
    assert content.exam_type is ExamType.MIDTERM
    assert content.term == "2026 Spring"
    assert content.kb_version == KB_VERSION
    assert content.generated_at == GENERATED_AT
    # Satisfied(1.0) + Partial(0.5) + NotSatisfied(0.0) = 1.5 / 3 * 100 = 50.00
    assert content.score == 50
    assert content.denominator == 3
    assert content.satisfied_count == 1
    assert content.partially_satisfied_count == 1
    assert content.not_satisfied_count == 1
    assert content.not_verified_count == 1
    assert content.not_applicable_count == 1
    assert len(content.findings) == 5


def test_assemble_report_content_insufficient_evidence_for_zero_denominator() -> None:
    analysis = _analysis()
    findings = [_finding(analysis.id, "REQ009", "RULE009", AcademicStatus.NOT_VERIFIED)]

    content = assemble_report_content(analysis, findings, KB_SOURCE, GENERATED_AT)

    assert content.score is None
    assert content.score_label == "Insufficient Evidence"
    assert content.denominator == 0


def test_missing_evidence_property_returns_only_not_verified_findings() -> None:
    analysis = _analysis()
    findings = [
        _finding(analysis.id, "REQ001", "RULE001", AcademicStatus.SATISFIED),
        _finding(analysis.id, "REQ009", "RULE009", AcademicStatus.NOT_VERIFIED),
    ]

    content = assemble_report_content(analysis, findings, KB_SOURCE, GENERATED_AT)

    assert len(content.missing_evidence) == 1
    assert content.missing_evidence[0].requirement_id == "REQ009"


def test_finding_entry_carries_official_requirement_display_metadata() -> None:
    analysis = _analysis()
    findings = [_finding(analysis.id, "REQ018", "RULE018", AcademicStatus.SATISFIED)]

    content = assemble_report_content(analysis, findings, KB_SOURCE, GENERATED_AT)

    entry = content.findings[0]
    assert entry.requirement_name == "Correct Total Marks"
    assert entry.dimension == "Marks and Totals"
    assert entry.source_type == "Derived Exam Requirement"
    assert entry.officiality == "Derived"


def test_finding_entry_carries_matching_recommendation() -> None:
    analysis = _analysis()
    findings = [_finding(analysis.id, "REQ001", "RULE001", AcademicStatus.PARTIALLY_SATISFIED)]

    content = assemble_report_content(analysis, findings, KB_SOURCE, GENERATED_AT)

    entry = content.findings[0]
    assert len(entry.recommendations) == 1
    assert entry.recommendations[0].recommendation_id == "REC001"


def test_finding_entry_carries_evidence_citations() -> None:
    analysis = _analysis()
    ev = Evidence(
        id=uuid.uuid4(),
        analysis_id=analysis.id,
        source_document=UploadedFileType.EXAM,
        evidence_type="question_text",
        page_number=2,
        item_reference="Q1",
        extracted_text="Q1 text",
        confidence=1.0,
    )
    findings = [
        _finding(analysis.id, "REQ019", "RULE019", AcademicStatus.SATISFIED, evidence=[ev]),
    ]

    content = assemble_report_content(analysis, findings, KB_SOURCE, GENERATED_AT)

    entry = content.findings[0]
    assert len(entry.evidence) == 1
    assert entry.evidence[0].item_reference == "Q1"
    assert entry.evidence[0].page_number == 2
    assert entry.evidence[0].source_document == UploadedFileType.EXAM


def test_assemble_report_content_handles_zero_findings() -> None:
    analysis = _analysis()
    content = assemble_report_content(analysis, [], KB_SOURCE, GENERATED_AT)

    assert content.findings == ()
    assert content.missing_evidence == ()
    assert content.score is None
    assert content.score_label == "Insufficient Evidence"


def test_report_content_preserves_semantic_confidence_and_derived_relationships() -> None:
    from app.core.domain import SemanticConfidenceLevel

    analysis = _analysis()
    question = Evidence(
        id=uuid.uuid4(),
        analysis_id=analysis.id,
        source_document=UploadedFileType.EXAM,
        evidence_type="question_text",
        page_number=1,
        item_reference="Q1",
        extracted_text="Explain software testing.",
        confidence=1.0,
    )
    clo = Evidence(
        id=uuid.uuid4(),
        analysis_id=analysis.id,
        source_document=UploadedFileType.TP153,
        evidence_type="clo",
        page_number=3,
        item_reference="CLO1",
        extracted_text="Explain software quality concepts.",
        confidence=1.0,
    )
    finding = _finding(
        analysis.id,
        "REQ001",
        "RULE001",
        AcademicStatus.SATISFIED,
        evidence=[question, clo],
    )
    finding.evaluator_type = "semantic_ai"
    finding.confidence_level = SemanticConfidenceLevel.HIGH
    finding.ai_provider = "fake"
    finding.ai_model = "fake-semantic-v1"
    finding.prompt_template_version = "semantic-rule-v1"
    finding.kb_version = "1.0"
    finding.evaluation_details = {
        "schema_version": 1,
        "decision": "Satisfied",
        "evidence_used": [str(question.id), str(clo.id)],
        "reasoning": "The confirmed question is related to the confirmed CLO.",
        "recommendation": None,
        "confidence_basis": ["All required question items were judged."],
        "item_judgments": [
            {
                "source_evidence_id": str(question.id),
                "target_evidence_ids": [str(clo.id)],
                "status": "Satisfied",
                "reasoning": "The concepts match within the controlled evidence set.",
            }
        ],
        "retrieved_knowledge_ids": ["REQ001", "RULE001"],
    }

    content = assemble_report_content(analysis, [finding], KB_SOURCE, GENERATED_AT)
    entry = content.findings[0]

    assert entry.confidence_level is SemanticConfidenceLevel.HIGH
    assert entry.evaluation_reasoning == ("The confirmed question is related to the confirmed CLO.")
    assert entry.confidence_basis == ("All required question items were judged.",)
    assert entry.contains_derived_relationships is True
    assert len(entry.item_judgments) == 1
    judgment = entry.item_judgments[0]
    assert judgment.source_evidence is not None
    assert judgment.source_evidence.item_reference == "Q1"
    assert [item.item_reference for item in judgment.target_evidence] == ["CLO1"]
    assert judgment.reasoning == "The concepts match within the controlled evidence set."
    assert entry.retrieved_knowledge_ids == ("REQ001", "RULE001")


def test_report_content_includes_assessment_records_and_runtime_coverage() -> None:
    from app.models.assessment_record import AssessmentRecord
    from app.services.rules.coverage_audit import build_rule_coverage_audit

    analysis = _analysis()
    finding = _finding(analysis.id, "REQ018", "RULE018", AcademicStatus.SATISFIED)
    assessment = AssessmentRecord(
        id=uuid.uuid4(),
        analysis_id=analysis.id,
        method="Written exam",
        activity="Midterm",
        percentage=30,
        page_number=5,
        confidence=1.0,
    )
    coverage = build_rule_coverage_audit(analysis.id, [finding])

    content = assemble_report_content(
        analysis,
        [finding],
        KB_SOURCE,
        GENERATED_AT,
        assessment_records=[assessment],
        rule_coverage=coverage,
    )

    assert content.assessment_records[0].method == "Written exam"
    assert content.assessment_records[0].percentage == 30
    assert content.rule_coverage is coverage
    rule018 = next(item for item in coverage.entries if item.rule_id == "RULE018")
    assert rule018.finding_status is AcademicStatus.SATISFIED
    assert coverage.not_run_rules > 0
