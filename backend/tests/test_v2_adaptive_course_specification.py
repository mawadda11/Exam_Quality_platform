from __future__ import annotations

from app.services.extraction.digital_tp153_extractor import (
    AdaptiveCourseSpecificationExtractor,
    CourseSpecificationLine,
)
from app.services.extraction.language_detection import TextLanguage
from app.services.extraction.types import Geometry


def _line(text: str, page: int = 1, confidence: float = 1.0) -> CourseSpecificationLine:
    return CourseSpecificationLine(
        text=text,
        page_number=page,
        confidence=confidence,
        geometry=Geometry(10, 10, 500, 30),
    )


def test_section_heading_layout_extracts_explicit_english_records() -> None:
    result = AdaptiveCourseSpecificationExtractor().parse_lines(
        [
            _line("Course Learning Outcomes"),
            _line("CLO1: Explain database concepts. [PLO2]"),
            _line("CLO2: Apply normalization techniques."),
            _line("Course Topics"),
            _line("T1: Database foundations - 3 hours"),
            _line("Assessment Methods", 2),
            _line("Method: Midterm | Activity: Written Exam | Percentage: 30%", 2),
        ]
    )

    assert result.layout_family == "section_heading"
    assert result.document_language == TextLanguage.ENGLISH
    assert [(item.code, item.program_outcome_reference) for item in result.clos] == [
        ("CLO1", "PLO2"),
        ("CLO2", None),
    ]
    assert result.topics[0].expected_hours == 3.0
    assert result.assessment_records[0].percentage == 30.0
    assert result.missing_sections == []


def test_reordered_arabic_table_layout_is_review_ready_without_invention() -> None:
    result = AdaptiveCourseSpecificationExtractor().parse_lines(
        [
            _line("رمز المقرر: CPIT-450"),
            _line("طرق التقييم"),
            _line("اختبار نصفي | اختبار تحريري | ٢٠٪"),
            _line("موضوعات المقرر"),
            _line("١ | التطبيع | ٣ ساعات"),
            _line("مخرجات التعلم"),
            _line("CLO١ | شرح مفاهيم قواعد البيانات | PLO٢"),
        ]
    )

    assert result.layout_family == "table_led"
    assert result.document_language == TextLanguage.ARABIC
    assert result.course_fields[0].field_name == "course_code"
    assert result.course_fields[0].value == "CPIT-450"
    assert result.clos[0].code == "CLO1"
    assert result.clos[0].text == "شرح مفاهيم قواعد البيانات"
    assert result.clos[0].program_outcome_reference == "PLO2"
    assert result.topics[0].code == "T1"
    assert result.topics[0].expected_hours == 3.0
    assert result.assessment_records[0].method == "اختبار نصفي"
    assert result.assessment_records[0].percentage == 20.0
    assert result.missing_sections == []


def test_compact_layout_extracts_only_explicit_values_and_marks_missing_topics() -> None:
    result = AdaptiveCourseSpecificationExtractor().parse_lines(
        [
            _line("Course Code CS101"),
            _line("Course Name Introduction to Programming"),
            _line("CLO1 Explain programming concepts"),
            _line("CLO2 Develop simple Python programs"),
            _line("Assessment Midterm 30%, Final 50%, Assignments 20%"),
        ]
    )

    assert result.layout_family == "compact"
    assert [field.field_name for field in result.course_fields] == ["course_code", "course_name"]
    assert [item.code for item in result.clos] == ["CLO1", "CLO2"]
    assert result.topics == []
    assert [item.section for item in result.missing_sections] == ["topics"]
    assert [item.percentage for item in result.assessment_records] == [30.0, 50.0, 20.0]


def test_low_confidence_source_remains_low_confidence_for_human_review() -> None:
    result = AdaptiveCourseSpecificationExtractor().parse_lines(
        [
            _line("Course Learning Outcomes"),
            _line("CLO1: Explain database concepts.", confidence=0.62),
        ]
    )

    assert result.clos[0].confidence == 0.62
    assert result.topics == []
    assert {item.section for item in result.missing_sections} == {
        "topics",
        "assessment_records",
    }


def test_missing_sections_never_create_placeholder_domain_rows() -> None:
    result = AdaptiveCourseSpecificationExtractor().parse_lines([_line("Course Code: IT101")])

    assert result.clos == []
    assert result.topics == []
    assert result.assessment_records == []
    assert {item.section for item in result.missing_sections} == {
        "clos",
        "topics",
        "assessment_records",
    }


def test_mixed_reordered_layout_preserves_pages_confidence_and_provenance() -> None:
    result = AdaptiveCourseSpecificationExtractor().parse_lines(
        [
            _line("طرق التقييم", page=4),
            _line("Midterm | Written exam | 30%", page=4, confidence=0.91),
            _line("Course Topics", page=2),
            _line("T1 | هياكل البيانات | 4 hours", page=2, confidence=0.87),
            _line("مخرجات التعلم", page=3),
            _line("CLO1 | Explain هياكل البيانات | PLO2", page=3, confidence=0.89),
        ]
    )

    assert result.document_language == TextLanguage.MIXED
    assert result.layout_family == "table_led"
    assert result.clos[0].page_number == 3
    assert result.clos[0].confidence == 0.801
    assert result.clos[0].geometry is not None
    assert result.topics[0].page_number == 2
    assert result.assessment_records[0].page_number == 4
    assert result.missing_sections == []


def test_duplicate_and_low_confidence_records_emit_review_warnings() -> None:
    result = AdaptiveCourseSpecificationExtractor().parse_lines(
        [
            _line("Course Learning Outcomes"),
            _line("CLO1: Explain databases.", confidence=0.68),
            _line("CLO1: Apply databases.", confidence=0.9),
            _line("Course Topics"),
            _line("T1: Database foundations - 3 hours"),
            _line("Assessment Methods"),
            _line("Midterm | Written exam | 30%"),
        ]
    )

    warning_codes = {warning.code for warning in result.review_warnings}
    assert "duplicate_conflicting_code" in warning_codes
    assert all(warning.page_number >= 1 for warning in result.review_warnings)
