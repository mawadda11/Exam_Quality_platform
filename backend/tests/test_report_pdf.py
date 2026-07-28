from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO

import pdfplumber

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


def _pdf_text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


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


def test_render_report_pdf_keeps_internal_assessments_and_coverage_out_of_user_report() -> None:
    from app.core.domain import SemanticConfidenceLevel
    from app.schemas.rule_coverage import (
        RuleCoverageAuditResponse,
        RuleCoverageEntryResponse,
        RuleRuntimeDisposition,
    )
    from app.services.reporting.content import (
        ReportAssessmentRecordEntry,
        ReportItemJudgment,
    )
    from app.services.rules.capability_manifest import (
        DesignDisposition,
        EvaluationMode,
        SupportStatus,
    )

    source = EvidenceCitation(
        id=uuid.uuid4(),
        source_document=UploadedFileType.EXAM,
        evidence_type="question_text",
        page_number=1,
        item_reference="Q1",
    )
    target = EvidenceCitation(
        id=uuid.uuid4(),
        source_document=UploadedFileType.TP153,
        evidence_type="clo",
        page_number=3,
        item_reference="CLO1",
    )
    judgment = ReportItemJudgment(
        source_evidence_id=source.id,  # type: ignore[arg-type]
        source_evidence=source,
        target_evidence_ids=(target.id,),  # type: ignore[arg-type]
        target_evidence=(target,),
        unresolved_target_evidence_ids=(),
        status=AcademicStatus.SATISFIED,
        reasoning="The controlled concepts align.",
    )
    entry = _finding_entry(
        requirement_id="REQ001",
        rule_id="RULE001",
        confidence_level=SemanticConfidenceLevel.HIGH,
        evaluation_reasoning="The confirmed evidence supports the relationship.",
        confidence_basis=("All required items were judged.",),
        item_judgments=(judgment,),
        retrieved_knowledge_ids=("REQ001", "RULE001"),
        evidence=(source, target),
    )
    coverage = RuleCoverageAuditResponse(
        analysis_id=uuid.uuid4(),
        total_rules=1,
        evaluated_rules=1,
        conditional_capability_gap_rules=0,
        unsupported_rules=0,
        not_run_rules=0,
        runtime_integrity_ok=True,
        entries=[
            RuleCoverageEntryResponse(
                requirement_id="REQ001",
                rule_id="RULE001",
                requirement_name="Question-to-CLO Mapping",
                rule_name="CLO Mapping",
                support_status=SupportStatus.SUPPORTED,
                evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
                design_disposition=DesignDisposition.DESIGN_AUTHORIZED,
                runtime_disposition=RuleRuntimeDisposition.EVALUATED,
                finding_status=AcademicStatus.SATISFIED,
                evaluator_type="semantic_ai",
            )
        ],
    )
    content = _content(
        findings=(entry,),
        assessment_records=(
            ReportAssessmentRecordEntry(
                method="Written exam",
                activity="Midterm",
                percentage=30,
                page_number=5,
            ),
        ),
        rule_coverage=coverage,
    )

    pdf_bytes = render_report_pdf(content)
    text = _pdf_text(pdf_bytes)

    assert pdf_bytes.startswith(b"%PDF")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert "Evidence-linked item judgments" in text
    assert "TP-153 Assessment Source Records" not in text
    assert "Rule Execution Coverage" not in text
    assert "Earned credit:" not in text


def test_render_report_pdf_supports_arabic_and_mixed_unicode_evidence() -> None:
    entry = _finding_entry(
        requirement_name="وضوح السؤال",
        explanation="السؤال يطلب كتابة استعلام SQL ويحتوي على دليل عربي واضح.",
        evidence=(
            EvidenceCitation(
                source_document=UploadedFileType.EXAM,
                evidence_type="question_text",
                page_number=1,
                item_reference="س٣ / Q3",
            ),
        ),
        recommendations=(
            RecommendationDisplay(
                recommendation_id="REC-AR",
                rule_id="RULE018",
                title="مراجعة الصياغة",
                text="حافظ على النص العربي وأسماء SQL دون استبدال الأحرف.",
                target_user="Faculty",
                recommendation_type="Corrective",
            ),
        ),
    )
    pdf_bytes = render_report_pdf(
        _content(
            course_name="قواعد البيانات المتقدمة",
            term="الفصل الثاني ٢٠٢٦",
            findings=(entry,),
        )
    )

    assert pdf_bytes.startswith(b"%PDF")
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert len(pdf_bytes) > 0


def test_report_renderer_enables_harfbuzz_and_detects_arabic_paragraphs(monkeypatch) -> None:
    from fpdf import FPDF

    from app.services.reporting import pdf as report_pdf

    calls: list[bool] = []

    def fake_set_text_shaping(self: FPDF, use_shaping_engine: bool = True, **_: object) -> None:
        calls.append(use_shaping_engine)

    monkeypatch.setattr(FPDF, "set_text_shaping", fake_set_text_shaping)
    rendered = report_pdf.render_report_pdf(
        _content(course_name="قواعد البيانات المتقدمة", term="الفصل الثاني ٢٠٢٦")
    )

    assert rendered.startswith(b"%PDF")
    assert calls == [True]
    assert report_pdf._is_predominantly_arabic("اختبار نصفي") is True
    assert report_pdf._is_predominantly_arabic("Related evidence: اختبار نصفي") is False
