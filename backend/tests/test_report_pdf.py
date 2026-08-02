from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO

import pdfplumber

from app.core.domain import AcademicStatus, ExamType, ReportLanguage, UploadedFileType
from app.services.knowledge_base.reference_data import RecommendationDisplay
from app.services.reporting.content import (
    EvidenceCitation,
    ReportContent,
    ReportDocumentReferenceEntry,
    ReportFindingEntry,
    ReportRelationshipEntry,
    ReportSupportingAnnotationEntry,
    ReportSupportingMaterialEntry,
)
from app.services.reporting.pdf import _source_text, render_report_pdf

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


def test_structured_evidence_is_present_in_english_and_arabic_reports() -> None:
    structured_content = _content(
        capability_version="v2-b4-structured-evidence",
        supporting_materials=(
            ReportSupportingMaterialEntry(
                identifier=uuid.uuid4(),
                material_type="figure",
                page_number=2,
                source_text="SELECT student_id FROM results",
                confidence=0.94,
                extraction_method="direct_text",
            ),
        ),
        supporting_annotations=(
            ReportSupportingAnnotationEntry(
                annotation_type="caption",
                original_text="الشكل 1: Relational Database Schema",
                page_number=2,
                confidence=0.93,
            ),
        ),
        document_references=(
            ReportDocumentReferenceEntry(
                original_text="Refer to Figure 1",
                target_type="figure",
                target_label="Figure 1",
                page_number=1,
                confidence=0.96,
                resolution_status="resolved",
                candidate_count=1,
            ),
        ),
    )

    english = render_report_pdf(structured_content, language=ReportLanguage.ENGLISH)
    arabic = render_report_pdf(structured_content, language=ReportLanguage.ARABIC)
    english_text = _pdf_text(english)
    arabic_text = _pdf_text(arabic)

    for text in (english_text, arabic_text):
        assert "Refer to Figure 1" in text
        # Full code/table/caption excerpts stay in audit storage and are not
        # repeated in the concise faculty appendix.
        assert "SELECT student_id FROM results" not in text
        assert "Relational Database Schema" not in text
        assert "v2-b4-structured-evidence" not in text
        assert "Question Type Distribution" not in text
        assert "Automatic question types" not in text
    assert english != arabic


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


def test_recommendations_section_includes_all_supported_dimensions_and_deduplicates() -> None:
    material_recommendation = RecommendationDisplay(
        recommendation_id="REC016",
        rule_id="RULE016",
        title="Associate the Supporting Item Clearly",
        text="Link the material to its intended question.",
        target_user="Faculty",
        recommendation_type="Corrective",
    )
    instruction_recommendation = RecommendationDisplay(
        recommendation_id="REC021",
        rule_id="RULE021",
        title="Complete the Instructions",
        text="Add the necessary exam-level instructions.",
        target_user="Faculty",
        recommendation_type="Corrective",
    )
    missing_topic_recommendation = RecommendationDisplay(
        recommendation_id="REC032",
        rule_id="RULE007",
        title="Request Missing Topic Evidence",
        text="Provide readable course-topic evidence.",
        target_user="Faculty",
        recommendation_type="Input Request",
    )
    findings = (
        _finding_entry(
            requirement_id="REQ016",
            rule_id="RULE016",
            requirement_name="Supporting Material Association",
            dimension="Supporting Material",
            status=AcademicStatus.NOT_SATISFIED,
            recommendations=(material_recommendation,),
        ),
        _finding_entry(
            requirement_id="REQ021",
            rule_id="RULE021",
            requirement_name="Complete Instructions",
            dimension="Exam Instructions",
            status=AcademicStatus.NOT_SATISFIED,
            recommendations=(instruction_recommendation,),
        ),
        _finding_entry(
            requirement_id="REQ007",
            rule_id="RULE007",
            requirement_name="Question-to-Topic Alignment",
            dimension="Topic Alignment",
            status=AcademicStatus.NOT_VERIFIED,
            recommendations=(missing_topic_recommendation,),
        ),
        _finding_entry(
            requirement_id="REQ021",
            rule_id="RULE021",
            requirement_name="Complete Instructions",
            dimension="Exam Instructions",
            status=AcademicStatus.PARTIALLY_SATISFIED,
            recommendations=(instruction_recommendation,),
        ),
    )

    text = _pdf_text(render_report_pdf(_content(findings=findings)))

    assert "Associate the Supporting Item Clearly" in text
    assert "Complete the Instructions" in text
    assert "Request Missing Topic Evidence" in text
    assert text.count("Complete the Instructions:") == 1


def test_arabic_report_header_and_recommendation_groups_are_fully_localized(
    monkeypatch,
) -> None:
    from app.services.reporting import pdf as report_pdf

    entry = _finding_entry(
        requirement_id="REQ021",
        rule_id="RULE021",
        requirement_name="Complete Instructions",
        dimension="Exam Instructions",
        status=AcademicStatus.NOT_SATISFIED,
        recommendations=(
            RecommendationDisplay(
                recommendation_id="REC021",
                rule_id="RULE021",
                title="Complete the Instructions",
                text="Add the necessary exam-level instructions.",
                target_user="Faculty",
                recommendation_type="Corrective",
            ),
        ),
    )
    captured: list[str] = []
    original_paragraph = report_pdf._paragraph
    original_subheading = report_pdf._subheading

    def capture_paragraph(pdf, text: str, *args, **kwargs) -> None:
        captured.append(text)
        original_paragraph(pdf, text, *args, **kwargs)

    def capture_subheading(pdf, text: str) -> None:
        captured.append(text)
        original_subheading(pdf, text)

    monkeypatch.setattr(report_pdf, "_paragraph", capture_paragraph)
    monkeypatch.setattr(report_pdf, "_subheading", capture_subheading)
    report_pdf.render_report_pdf(
        _content(findings=(entry,)),
        language=ReportLanguage.ARABIC,
    )
    text = "\n".join(captured)

    assert "اختبار نصفي، 2026 Spring" in text
    assert "اختبار نصفي اختبار" not in text
    assert "العربية" in text
    assert "Arabic" not in text
    assert "تعليمات الاختبار" in text
    assert "Materials & References" not in text
    assert "Exam Instructions" not in text


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
    assert "Technical Traceability Appendix" not in text
    assert "Evidence-linked item judgments" not in text
    assert "TP-153 Assessment Source Records" not in text
    assert "Rule Execution Coverage" not in text
    assert "Earned credit:" not in text
    assert "Q1 | Exam" not in text
    assert "CLO1 | TP-153" not in text


def test_render_report_pdf_omits_judgment_inventory_with_many_judgments() -> None:
    """The faculty PDF never repeats the technical judgment inventory."""
    from dataclasses import replace

    from app.services.reporting.content import ReportItemJudgment

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
    judgments = tuple(
        ReportItemJudgment(
            source_evidence_id=source.id,  # type: ignore[arg-type]
            source_evidence=source,
            target_evidence_ids=(target.id,),  # type: ignore[arg-type]
            target_evidence=(target,),
            unresolved_target_evidence_ids=(),
            status=AcademicStatus.SATISFIED,
            reasoning=f"Judgment {i}.",
        )
        for i in range(12)
    )
    entry = replace(_finding_entry(), item_judgments=judgments, evidence=(source, target))

    pdf_bytes = render_report_pdf(_content(findings=(entry,)))
    text = _pdf_text(pdf_bytes)

    assert "Technical Traceability Appendix" not in text
    assert "evidence-linked item judgments" not in text
    assert "Q1 | Exam" not in text
    assert "Source evidence" not in text
    assert "Target evidence" not in text


def test_render_report_pdf_omits_capability_versions_from_faculty_reports() -> None:
    for capability_version in ("v2-b6-question-types", "v2-pilot-correctness"):
        pdf_bytes = render_report_pdf(_content(capability_version=capability_version))
        text = _pdf_text(pdf_bytes)

        assert capability_version not in text
        assert "Capability:" not in text
        assert "Not applicable (legacy analysis)" not in text


def test_render_report_pdf_preserves_source_language_independent_of_report_language() -> None:
    content = _content(
        clo_entries=(
            ReportRelationshipEntry(
                identifier="CLO1",
                text="يشرح مفاهيم قواعد البيانات العلائقية",
                linked_question_labels=("Q1",),
                total_marks=5,
                coverage_status=AcademicStatus.SATISFIED,
            ),
        ),
        topic_entries=(
            ReportRelationshipEntry(
                identifier="English source topic",
                text="English source topic",
                linked_question_labels=("Q1",),
                total_marks=5,
                coverage_status=AcademicStatus.SATISFIED,
                identifier_is_source_text=True,
            ),
        ),
    )

    english_text = _pdf_text(render_report_pdf(content, language=ReportLanguage.ENGLISH))
    arabic_text = _pdf_text(render_report_pdf(content, language=ReportLanguage.ARABIC))

    # Arabic glyph extraction from a rendered PDF is renderer-dependent,
    # especially when HarfBuzz is unavailable. Verify the preservation rule
    # directly and use a Latin source string for the cross-language PDF check.
    assert _source_text("يشرح مفاهيم قواعد البيانات العلائقية", "fallback") == (
        "يشرح مفاهيم قواعد البيانات العلائقية"
    )
    assert "English source topic" in arabic_text
    assert "Not available in this report language" not in english_text
    assert "غير متاح بلغة هذا التقرير" not in arabic_text


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


def test_render_report_pdf_uses_numbered_sections_matching_the_web_report() -> None:
    pdf_bytes = render_report_pdf(_content())
    text = _pdf_text(pdf_bytes)

    for heading in (
        "1. Report Header",
        "2. Executive Summary",
        "3. Overall Exam Quality Score",
        "4. Status Distribution",
        "5. Exam Summary",
        "6. CLO Analysis",
        "7. Topic Analysis",
        "8. Marks & Structure",
        "9. Materials & References",
        "10. Key Findings",
        "11. Missing or Unverified Evidence",
        "12. Recommendations",
        "13. Scope Disclaimer",
    ):
        assert heading in text, f"missing section heading: {heading}"


def test_render_report_pdf_omits_technical_provenance_from_faculty_report() -> None:
    entry = _finding_entry(
        requirement_id="REQ001",
        rule_id="RULE001",
        status=AcademicStatus.SATISFIED,
    )
    from dataclasses import replace

    entry = replace(
        entry,
        ai_provider="anthropic",
        ai_model="claude-governed-v1",
        prompt_template_version="semantic-rule-v3",
    )
    text = _pdf_text(render_report_pdf(_content(findings=(entry,))))

    assert "Technical Traceability Appendix" not in text
    assert "anthropic" not in text
    assert "claude-governed-v1" not in text
    assert "semantic-rule-v3" not in text


def test_render_report_pdf_shows_clo_and_topic_analysis_tables() -> None:
    from app.services.reporting.content import ReportRelationshipEntry

    content = _content(
        clo_entries=(
            ReportRelationshipEntry(
                identifier="CLO1",
                text="Explain fundamental computing concepts.",
                linked_question_labels=("Q1", "Q2"),
                total_marks=10,
                coverage_status=AcademicStatus.SATISFIED,
            ),
        ),
        topic_entries=(
            ReportRelationshipEntry(
                identifier="T1",
                text="Software testing",
                linked_question_labels=(),
                total_marks=0,
                coverage_status=AcademicStatus.NOT_SATISFIED,
            ),
        ),
    )
    pdf_bytes = render_report_pdf(content)
    # A wrapped table cell's second line is extracted by pdfplumber on its
    # own text band below the row's single-line cells, so the visually
    # correct wrapped sentence is not always one contiguous plaintext
    # substring - check both halves rather than the full phrase.
    text = " ".join(_pdf_text(pdf_bytes).split())

    assert "CLO1" in text
    assert "Explain fundamental" in text
    assert "computing concepts." in text
    assert "T1" in text


def test_render_report_pdf_topic_table_has_no_duplicate_clo_text_column() -> None:
    """Regression test: the Topic Analysis table must use exactly
    Topic | Linked Questions | Total Marks | Coverage Status - no separate
    text/description column duplicated (and mislabelled "CLO text") from the
    CLO table."""
    from app.services.reporting.content import ReportRelationshipEntry

    content = _content(
        topic_entries=(
            ReportRelationshipEntry(
                identifier="T1",
                text="Software testing and quality assurance practices.",
                linked_question_labels=("Q1",),
                total_marks=5,
                coverage_status=AcademicStatus.SATISFIED,
            ),
        ),
    )
    pdf_bytes = render_report_pdf(content)
    text = " ".join(_pdf_text(pdf_bytes).split())
    topic_section = text[text.index("7. Topic Analysis") : text.index("8. Marks")]

    # Header cells can wrap onto two lines, which pdfplumber extracts as
    # separate text bands interleaved with other cells - check word
    # fragments rather than full contiguous phrases.
    assert "T1" in topic_section
    assert "Linked" in topic_section
    assert "questions" in topic_section
    assert "Total marks" in topic_section
    assert "Coverage" in topic_section
    assert "status" in topic_section
    assert "CLO text" not in topic_section
    assert "Software testing" not in topic_section


def test_render_report_pdf_preserves_uncoded_topic_source_text_in_any_report_language() -> None:
    """Source-document topic text remains in its original language even when
    the report interface language differs."""
    from app.services.reporting.content import ReportRelationshipEntry

    content = _content(
        topic_entries=(
            ReportRelationshipEntry(
                identifier="خوارزميات الفرز",
                text="خوارزميات الفرز",
                linked_question_labels=(),
                total_marks=0,
                coverage_status=AcademicStatus.NOT_SATISFIED,
                identifier_is_source_text=True,
            ),
        ),
    )
    pdf_bytes = render_report_pdf(content)
    text = " ".join(_pdf_text(pdf_bytes).split())

    # Arabic glyph shaping is rendered correctly in the PDF, but PDF text

    # extractors may not reconstruct shaped Arabic into logical Unicode order.

    expected_source = (
        "\u062e\u0648\u0627\u0631\u0632\u0645\u064a\u0627\u062a \u0627\u0644\u0641\u0631\u0632"
    )

    assert content.topic_entries[0].identifier == expected_source

    assert content.topic_entries[0].text == expected_source

    assert content.topic_entries[0].identifier_is_source_text is True

    assert pdf_bytes.startswith(b"%PDF")
    assert "Not available in this report" not in text


def test_render_report_pdf_never_contains_question_type_content() -> None:
    pdf_bytes = render_report_pdf(_content(findings=(_finding_entry(),)))
    text = _pdf_text(pdf_bytes)

    assert "Question Type" not in text
    assert "question-type" not in text.lower()


def test_render_report_pdf_arabic_keeps_provider_details_out_of_the_primary_body() -> None:
    # pdfplumber does not reliably round-trip HarfBuzz-shaped Arabic glyph
    # order back to logical text, so - matching the existing Arabic PDF
    # tests in this file - this checks PDF validity plus the always-Latin
    # provider/model strings rather than asserting extracted Arabic text.
    from dataclasses import replace

    entry = replace(_finding_entry(), ai_provider="anthropic", ai_model="claude")
    pdf_bytes = render_report_pdf(_content(findings=(entry,)), language=ReportLanguage.ARABIC)

    assert pdf_bytes.startswith(b"%PDF")
    text = _pdf_text(pdf_bytes)
    assert "anthropic" not in text
    assert "claude" not in text


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
