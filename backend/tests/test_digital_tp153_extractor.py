from __future__ import annotations

from pathlib import Path

import pytest
from helpers import corrupted_pdf_bytes
from tp153_pdf_fixtures import (
    build_complete_tp153_pdf,
    build_incomplete_assessment_tp153_pdf,
    build_missing_clo_section_tp153_pdf,
    build_official_sample_format_tp153_pdf,
)

from app.services.extraction.digital_tp153_extractor import (
    CourseSpecificationLine,
    PdfPlumberTp153Extractor,
)
from app.services.extraction.types import ExtractionError


def _write(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def test_extracts_expected_clo_count_and_text(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "tp153.pdf", build_complete_tp153_pdf())

    result = PdfPlumberTp153Extractor().extract(pdf_path)

    assert [c.code for c in result.clos] == ["CLO1", "CLO2", "CLO3"]
    by_code = {c.code: c for c in result.clos}
    assert by_code["CLO1"].text == "Explain fundamental database design principles."
    assert by_code["CLO1"].program_outcome_reference == "PLO2"
    assert by_code["CLO2"].program_outcome_reference == "PLO3"


def test_extracts_expected_topic_count_text_and_hours(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "tp153.pdf", build_complete_tp153_pdf())

    result = PdfPlumberTp153Extractor().extract(pdf_path)

    assert [t.code for t in result.topics] == ["T1", "T2", "T3"]
    by_code = {t.code: t for t in result.topics}
    assert by_code["T1"].text == "Introduction to Databases"
    assert by_code["T1"].expected_hours == 3.0
    assert by_code["T2"].expected_hours == 4.0
    assert by_code["T3"].expected_hours == 5.0


def test_extracts_expected_assessment_method_activity_percentage(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "tp153.pdf", build_complete_tp153_pdf())

    result = PdfPlumberTp153Extractor().extract(pdf_path)

    by_method = {a.method: a for a in result.assessment_records}
    assert by_method["Midterm Exam"].activity == "Written Exam"
    assert by_method["Midterm Exam"].percentage == 20.0
    assert by_method["Final Exam"].percentage == 30.0
    assert by_method["Assignments"].activity == "Homework"
    assert by_method["Assignments"].percentage == 15.0


def test_extracts_expected_source_pages(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "tp153.pdf", build_complete_tp153_pdf())

    result = PdfPlumberTp153Extractor().extract(pdf_path)

    assert all(c.page_number == 1 for c in result.clos)
    assert all(t.page_number == 1 for t in result.topics)
    assert all(a.page_number == 2 for a in result.assessment_records)


def test_matched_records_have_full_confidence_and_geometry(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "tp153.pdf", build_complete_tp153_pdf())

    result = PdfPlumberTp153Extractor().extract(pdf_path)

    for clo in result.clos:
        assert clo.confidence == 1.0
        assert clo.geometry is not None
    for topic in result.topics:
        assert topic.confidence == 1.0
        assert topic.geometry is not None
    for record in result.assessment_records:
        assert record.confidence == 1.0
        assert record.geometry is not None


def test_complete_tp153_has_no_missing_sections(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "tp153.pdf", build_complete_tp153_pdf())

    result = PdfPlumberTp153Extractor().extract(pdf_path)

    assert result.missing_sections == []


def test_missing_clo_section_yields_zero_clos_and_a_missing_marker(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "tp153.pdf", build_missing_clo_section_tp153_pdf())

    result = PdfPlumberTp153Extractor().extract(pdf_path)

    # No CLO is invented when the section is absent.
    assert result.clos == []
    missing_sections = {m.section: m for m in result.missing_sections}
    assert "clos" in missing_sections
    assert missing_sections["clos"].note != ""

    # Topics and assessment records were present and are still extracted
    # normally - only the genuinely-absent section is flagged as missing.
    assert len(result.topics) == 2
    assert len(result.assessment_records) == 1
    assert "topics" not in missing_sections
    assert "assessment_records" not in missing_sections


def test_incomplete_assessment_line_keeps_method_and_activity_with_null_percentage(
    tmp_path: Path,
) -> None:
    pdf_path = _write(tmp_path, "tp153.pdf", build_incomplete_assessment_tp153_pdf())

    result = PdfPlumberTp153Extractor().extract(pdf_path)

    by_method = {a.method: a for a in result.assessment_records}
    assert by_method["Midterm Exam"].percentage == 20.0
    assert by_method["Lab Work"].activity == "Practical Session"
    assert by_method["Lab Work"].percentage is None
    # The incomplete record is not dropped, and no section is falsely
    # reported missing since at least one assessment record was found.
    assert result.missing_sections == []


def test_extracts_only_explicit_bundled_sample_tp153_records(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "sample-tp153.pdf", build_official_sample_format_tp153_pdf())

    result = PdfPlumberTp153Extractor().extract(pdf_path)

    assert [(clo.code, clo.text) for clo in result.clos] == [
        ("CLO1", "Explain programming concepts"),
        ("CLO2", "Develop simple Python programs"),
    ]
    assert result.topics == []
    assert [
        (record.method, record.activity, record.percentage) for record in result.assessment_records
    ] == [
        ("Midterm", None, 30.0),
        ("Final", None, 50.0),
        ("Assignments", None, 20.0),
    ]
    assert [missing.section for missing in result.missing_sections] == ["topics"]


def test_unparseable_pdf_raises_extraction_error_without_leaking_details(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "fake.pdf", corrupted_pdf_bytes())

    with pytest.raises(ExtractionError) as excinfo:
        PdfPlumberTp153Extractor().extract(pdf_path)

    assert "fake.pdf" in str(excinfo.value)


def test_assessment_header_role_accepts_common_assessment_column_name() -> None:
    from app.services.extraction.digital_tp153_extractor import _header_role, _table_section

    roles = tuple(_header_role(value) for value in ("Assessment", "Week", "Weight", "Notes"))

    assert roles == ("method", "week", "percentage", "notes")
    assert _table_section(roles) == "assessment_records"


def test_compact_clo_and_topic_metadata_are_separated_from_display_text() -> None:
    result = PdfPlumberTp153Extractor().parse_lines(
        [
            CourseSpecificationLine(text="Course Learning Outcomes", page_number=1),
            CourseSpecificationLine(
                text=(
                    "CLO1 | Explain relational database concepts, keys, constraints, "
                    "and Knowledge PLO1"
                ),
                page_number=1,
            ),
            CourseSpecificationLine(text="Course Topics", page_number=2),
            CourseSpecificationLine(
                text="T1 | Relational model, schemas, keys, and constraints 5",
                page_number=2,
            ),
        ]
    )

    assert result.clos[0].text == "Explain relational database concepts, keys, constraints"
    assert result.clos[0].program_outcome_reference == "PLO1"
    assert result.topics[0].text == "Relational model, schemas, keys, and constraints"
    assert result.topics[0].expected_hours == 5.0


def test_arabic_mixed_course_spec_sections_extract_all_clos_and_topics_without_collapsing_rows() -> None:
    result = PdfPlumberTp153Extractor().parse_lines(
        [
            CourseSpecificationLine(text="نواتج تعلم المقرر", page_number=1),
            CourseSpecificationLine(
                text="CLO1 شرح النموذج العلاقي والمفاتيح والقيود.",
                page_number=1,
            ),
            CourseSpecificationLine(
                text="CLO2 كتابة استعلامات SQL وربط الجداول باستخدام JOIN.",
                page_number=1,
            ),
            CourseSpecificationLine(
                text="CLO3 تحليل تصميم قاعدة البيانات وتطبيق 3NF.",
                page_number=1,
            ),
            CourseSpecificationLine(
                text="CLO4 تقييم المعاملات وأمن قواعد البيانات.",
                page_number=1,
            ),
            CourseSpecificationLine(text="موضوعات المقرر", page_number=2),
            CourseSpecificationLine(
                text="مقدمة في قواعد البيانات T1 والنموذج العلاقي",
                page_number=2,
            ),
            CourseSpecificationLine(
                text="SQL T2 الاستعلامات والتصفية والتجميع",
                page_number=2,
            ),
            CourseSpecificationLine(
                text="JOIN T3 والربط بين الجداول",
                page_number=2,
            ),
            CourseSpecificationLine(
                text="التطبيع T4 حتى 3NF",
                page_number=2,
            ),
            CourseSpecificationLine(
                text="المعاملات T5 وخصائص ACID",
                page_number=2,
            ),
            CourseSpecificationLine(
                text="أمن قواعد البيانات T6 و SQL Injection",
                page_number=2,
            ),
            CourseSpecificationLine(text="استراتيجيات التقييم", page_number=3),
            CourseSpecificationLine(text="Final Exam CLO1, CLO2, CLO3, CLO4", page_number=3),
        ]
    )

    assert [item.code for item in result.clos] == ["CLO1", "CLO2", "CLO3", "CLO4"]
    assert [item.code for item in result.topics] == ["T1", "T2", "T3", "T4", "T5", "T6"]
    assert result.topics[-1].text == "أمن قواعد البيانات و SQL Injection"
    assert all("Final Exam" not in item.text for item in result.topics)


def test_topic_dedupe_merges_coded_and_uncoded_recovery_of_same_source() -> None:
    from app.services.extraction.types import ExtractedTopic, Geometry

    coded = ExtractedTopic(
        code="T2",
        text="Relational model, keys, and integrity constraints",
        expected_hours=6.0,
        page_number=2,
        confidence=0.96,
        geometry=Geometry(x0=80, top=210, x1=470, bottom=232),
        source_text="T2 Relational model, keys, and integrity constraints 6",
    )
    recovered = ExtractedTopic(
        code=None,
        text="Relational model, keys, and integrity constraints",
        expected_hours=None,
        page_number=2,
        confidence=0.73,
        geometry=Geometry(x0=82, top=211, x1=468, bottom=233),
        source_text="Relational model, keys, and integrity constraints",
        extraction_method="recovery",
    )

    result = PdfPlumberTp153Extractor._dedupe_topics([coded, recovered])

    assert len(result) == 1
    assert result[0].code == "T2"
    assert result[0].expected_hours == 6.0


def test_topic_dedupe_preserves_distinct_explicit_codes() -> None:
    from app.services.extraction.types import ExtractedTopic, Geometry

    first = ExtractedTopic(
        code="T2",
        text="Database security",
        expected_hours=4.0,
        page_number=2,
        confidence=0.9,
        geometry=Geometry(x0=80, top=210, x1=470, bottom=232),
    )
    second = ExtractedTopic(
        code="T3",
        text="Database security",
        expected_hours=4.0,
        page_number=2,
        confidence=0.9,
        geometry=Geometry(x0=80, top=210, x1=470, bottom=232),
    )

    result = PdfPlumberTp153Extractor._dedupe_topics([first, second])

    assert [item.code for item in result] == ["T2", "T3"]
