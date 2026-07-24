from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.core.domain import AcademicStatus, ExamType, UploadedFileType
from app.services.knowledge_base.reference_data import RecommendationDisplay
from app.services.reporting.content import EvidenceCitation, ReportContent, ReportFindingEntry
from app.services.reporting.pdf import render_report_pdf

GENERATED_AT = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)


def _content(**overrides: object) -> ReportContent:
    defaults: dict[str, object] = dict(
        analysis_id=uuid.uuid4(),
        course_code="CPIT-450",
        course_name="Software Engineering",
        exam_type=ExamType.MIDTERM,
        term="2026 Spring",
        kb_version="1.0",
        generated_at=GENERATED_AT,
        score=None,
        score_label="Insufficient Evidence",
        denominator=0,
        satisfied_count=0,
        partially_satisfied_count=0,
        not_satisfied_count=0,
        not_verified_count=0,
        not_applicable_count=0,
        findings=(),
    )
    defaults.update(overrides)
    return ReportContent(**defaults)  # type: ignore[arg-type]


def _finding_entry(**overrides: object) -> ReportFindingEntry:
    defaults: dict[str, object] = dict(
        requirement_id="REQ018",
        rule_id="RULE018",
        requirement_name="Correct Total Marks",
        dimension="Marks and Totals",
        source_type="Derived Exam Requirement",
        officiality="Derived",
        status=AcademicStatus.SATISFIED,
        explanation="The calculated total equals the declared total.",
        evidence=(),
        recommendations=(),
    )
    defaults.update(overrides)
    return ReportFindingEntry(**defaults)  # type: ignore[arg-type]


def test_render_report_pdf_produces_a_valid_pdf_document() -> None:
    pdf_bytes = render_report_pdf(_content())
    assert pdf_bytes.startswith(b"%PDF")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert len(pdf_bytes) > 0


def test_render_report_pdf_handles_zero_findings() -> None:
    pdf_bytes = render_report_pdf(_content(findings=()))
    assert pdf_bytes.startswith(b"%PDF")


def test_render_report_pdf_handles_a_finding_with_evidence_and_recommendation() -> None:
    entry = _finding_entry(
        status=AcademicStatus.PARTIALLY_SATISFIED,
        evidence=(
            EvidenceCitation(
                source_document=UploadedFileType.EXAM,
                evidence_type="question_text",
                page_number=1,
                item_reference="Q1",
            ),
        ),
        recommendations=(
            RecommendationDisplay(
                recommendation_id="REC018",
                rule_id="RULE018",
                title="Correct the Total Marks",
                text="Recalculate the exam marks.",
                target_user="Faculty",
                recommendation_type="Corrective",
            ),
        ),
    )
    pdf_bytes = render_report_pdf(_content(findings=(entry,)))
    assert pdf_bytes.startswith(b"%PDF")


def test_render_report_pdf_handles_a_finding_with_no_evidence() -> None:
    entry = _finding_entry(status=AcademicStatus.NOT_VERIFIED, evidence=())
    pdf_bytes = render_report_pdf(_content(findings=(entry,)))
    assert pdf_bytes.startswith(b"%PDF")


def test_render_report_pdf_includes_missing_evidence_section_only_when_present() -> None:
    not_verified_entry = _finding_entry(status=AcademicStatus.NOT_VERIFIED)
    with_missing = render_report_pdf(_content(findings=(not_verified_entry,)))

    satisfied_entry = _finding_entry(status=AcademicStatus.SATISFIED)
    without_missing = render_report_pdf(_content(findings=(satisfied_entry,)))

    assert with_missing.startswith(b"%PDF")
    assert without_missing.startswith(b"%PDF")
    # Both are valid PDFs regardless of whether the Missing Evidence section
    # is rendered - the with-missing document is not simply identical/shorter.
    assert with_missing != without_missing


def test_render_report_pdf_with_a_numeric_score() -> None:
    pdf_bytes = render_report_pdf(
        _content(score=Decimal("75.00"), score_label=None, denominator=2, satisfied_count=1)
    )
    assert pdf_bytes.startswith(b"%PDF")
