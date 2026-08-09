from app.services.extraction.digital_pdf_extractor import (
    _joined_stem,
    _looks_like_page_footer_text,
)
from app.services.extraction.digital_tp153_extractor import (
    AdaptiveCourseSpecificationExtractor,
    CourseSpecificationLine,
)
from app.services.extraction.types import ExtractedTopic, Geometry


def test_page_footer_marker_is_detected_inside_real_footer_text() -> None:
    assert _looks_like_page_footer_text("CS 241 - Final Examination Page 2 of 7")
    assert _looks_like_page_footer_text("Final Exam - صفحة ٢ من ٧")


def test_joined_stem_excludes_page_furniture_without_course_specific_rules() -> None:
    stem = _joined_stem(
        [
            "Question 2: Explain the design decision.",
            "ANY 123 - Final Examination Page 2 of 7",
        ]
    )
    assert stem == "Question 2: Explain the design decision."


def test_structured_topic_preserves_code_and_contact_hours() -> None:
    extractor = AdaptiveCourseSpecificationExtractor()
    line = CourseSpecificationLine(
        text="CLO1, CLO2 | 6 | Relational model, keys, and integrity constraints | 2-3 | T2",
        page_number=2,
        confidence=0.95,
        geometry=Geometry(0, 100, 500, 130),
        raw_cells=("CLO1, CLO2", "6", "Relational model, keys, and integrity constraints", "2-3", "T2"),
        reading_cells=("CLO1, CLO2", "6", "Relational model, keys, and integrity constraints", "2-3", "T2"),
        cell_roles=("related_clos", "hours", "topic", "week", "code"),
        table_section="topics",
    )

    topic = extractor._parse_structured_topic(line)

    assert topic is not None
    assert topic.code == "T2"
    assert topic.expected_hours == 6
    assert topic.text == "Relational model, keys, and integrity constraints"


def test_topic_dedupe_prefers_structured_source_row_over_wrong_line_recovery() -> None:
    structured = ExtractedTopic(
        code="T2",
        text="Relational model, keys, and integrity constraints",
        expected_hours=6,
        page_number=2,
        confidence=0.98,
        geometry=Geometry(0, 100, 500, 130),
        source_text="CLO1, CLO2\n--- cell ---\n6\n--- cell ---\nRelational model, keys, and integrity constraints\n--- cell ---\n2-3\n--- cell ---\nT2",
        extraction_method="direct_text",
    )
    fallback = ExtractedTopic(
        code="T2",
        text="2-3 Relational model, keys, and integrity constraints 6 CLO1, CLO2",
        expected_hours=2,
        page_number=2,
        confidence=1.0,
        geometry=Geometry(10, 105, 490, 120),
    )

    result = AdaptiveCourseSpecificationExtractor._dedupe_topics([fallback, structured])

    assert len(result) == 1
    assert result[0].code == "T2"
    assert result[0].expected_hours == 6
    assert result[0].text == "Relational model, keys, and integrity constraints"
