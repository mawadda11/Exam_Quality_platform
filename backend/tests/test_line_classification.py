"""Unit tests for the line-classification rules shared by the digital and
OCR extraction paths (app.services.extraction.line_classification). Pure
text-in, dataclass-out - no PDF or OCR involved, so these run instantly and
pin down the actual decision rules independently of either extraction path.
"""

from __future__ import annotations

import pytest

from app.services.extraction.line_classification import (
    LineKind,
    classify_line,
    is_mark_status_annotation,
    parse_declared_total,
    strip_marks_annotations,
)


def test_question_line_sets_kind_and_label_and_becomes_new_parent() -> None:
    result = classify_line("Q3. Short answer questions.", current_parent_label="Q1")

    assert result.kind is LineKind.QUESTION
    assert result.number_label == "Q3"
    assert result.marks is None


@pytest.mark.parametrize("source", ["Question 1", "Question No. 2", "Question 3: Essay"])
def test_full_question_heading_is_recognized(source: str) -> None:
    result = classify_line(source, current_parent_label=None)

    assert result.kind is LineKind.QUESTION
    assert result.number_label is not None


def test_question_line_with_inline_marks_extracts_value_and_matched_text() -> None:
    result = classify_line("Q1. Explain normalization. [5 marks]", current_parent_label=None)

    assert result.marks is not None
    assert result.marks.value == 5.0
    assert result.marks.matched_text == "[5 marks]"


def test_bundled_sample_question_format_extracts_number_and_prefix_marks() -> None:
    result = classify_line(
        "Q1 (10): Define an algorithm and explain two characteristics.",
        current_parent_label=None,
    )

    assert result.kind is LineKind.QUESTION
    assert result.number_label == "Q1"
    assert result.marks is not None
    assert result.marks.value == 10.0
    assert result.marks.matched_text == "(10)"


def test_subquestion_line_builds_label_from_current_parent() -> None:
    result = classify_line("(a) Identify the primary key. [3 marks]", current_parent_label="Q2")

    assert result.kind is LineKind.SUBQUESTION
    assert result.number_label == "Q2(a)"
    assert result.marks is not None
    assert result.marks.value == 3.0


def test_subquestion_line_with_no_current_parent_omits_prefix() -> None:
    result = classify_line("(a) Orphaned subquestion.", current_parent_label=None)

    assert result.number_label == "(a)"


def test_instructions_line_is_classified_case_insensitively() -> None:
    result = classify_line("INSTRUCTIONS: Answer all questions.", current_parent_label=None)

    assert result.kind is LineKind.INSTRUCTIONS




def test_bilingual_instruction_heading_is_classified() -> None:
    result = classify_line("Instructions / التعليمات", current_parent_label=None)

    assert result.kind is LineKind.INSTRUCTIONS


@pytest.mark.parametrize(
    "source",
    [
        "Mark not stated",
        "Marks missing",
        "الدرجة غير مذكورة",
    ],
)
def test_mark_status_annotation_is_recognized(source: str) -> None:
    assert is_mark_status_annotation(source)


def test_inline_mark_status_annotation_is_removed_from_question_text() -> None:
    source = "Q3(c) Identify the default gateway that should be Mark not stated configured for LAN-A."

    cleaned = strip_marks_annotations(source)

    assert cleaned == "Q3(c) Identify the default gateway that should be configured for LAN-A."

def test_total_marks_line_is_classified() -> None:
    result = classify_line("Total Marks: 20", current_parent_label=None)

    assert result.kind is LineKind.TOTAL_MARKS


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Total Marks: 40", 40.0),
        ("Total Score – ٤٠", 40.0),
        ("Exam Total = ۴۰", 40.0),
        ("Maximum Marks 40", 40.0),
        ("Total: 40", 40.0),
        ("الدرجة الكلية: 40 درجة", 40.0),
        ("الدرجة الكلية للاختبار: ٤٠", 40.0),
        ("إجمالي الدرجات: ۴۰", 40.0),
        ("مجموع الدرجات 40", 40.0),
        ("المجموع الكلي: 40", 40.0),
        ("الدرجة النهائية ٤٠", 40.0),
        ("الدرجة الكلية: 40 درجة المدة: ساعتان", 40.0),
    ],
)
def test_declared_total_supports_approved_bilingual_labels_and_digits(
    source: str,
    expected: float,
) -> None:
    assert parse_declared_total(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "العام الجامعي: 1448",
        "المدة: ساعتان",
        "رمز المقرر: CS 241",
        "Page 2 of 7",
        "Q1 [6 marks]",
    ],
)
def test_declared_total_rejects_unrelated_exam_header_numbers(source: str) -> None:
    assert parse_declared_total(source) is None


def test_plain_prose_line_is_other_with_no_marks() -> None:
    result = classify_line("This is just a paragraph of exam preamble.", current_parent_label="Q1")

    assert result.kind is LineKind.OTHER
    assert result.number_label is None
    assert result.marks is None


def test_marks_bracket_on_a_non_question_line_is_not_surfaced() -> None:
    # Marks are only ever meaningful attached to a question/subquestion - an
    # OTHER-kind line's marks bracket (if any) is not surfaced, matching the
    # pre-existing digital extractor's behavior of only ever persisting marks
    # evidence for question/subquestion rows.
    result = classify_line("Some stray text [7 marks] here.", current_parent_label=None)

    assert result.kind is LineKind.OTHER
    assert result.marks is None


def test_technical_parenthesized_number_is_not_treated_as_marks() -> None:
    result = classify_line(
        "Q4. Perform the calculation in GF (19) and explain the result.",
        current_parent_label=None,
    )

    assert result.kind is LineKind.QUESTION
    assert result.marks is None


def test_bare_square_bracket_marks_remain_supported() -> None:
    result = classify_line("Q5. Explain the security property. [5]", current_parent_label=None)

    assert result.marks is not None
    assert result.marks.value == 5.0
    assert result.marks.matched_text == "[5]"


def test_decimal_question_label_preserves_hierarchy() -> None:
    result = classify_line("Q1.8 Which index is suitable? [1 marks]", current_parent_label="Q1")

    assert result.kind is LineKind.SUBQUESTION
    assert result.number_label == "Q1.8"
    assert result.marks is not None
    assert result.marks.value == 1.0


def test_inline_letter_question_label_preserves_hierarchy() -> None:
    result = classify_line("Q3(b) Explain partial dependency. [3 marks]", current_parent_label="Q3")

    assert result.kind is LineKind.SUBQUESTION
    assert result.number_label == "Q3(b)"
    assert result.marks is not None
    assert result.marks.value == 3.0


def test_strip_marks_annotations_removes_badge_from_middle_of_stem() -> None:
    from app.services.extraction.line_classification import strip_marks_annotations

    source = (
        "Q4(b) Write an SQL query to display each student name with the "
        "[3 marks] titles of courses in which the student is enrolled."
    )

    assert strip_marks_annotations(source) == (
        "Q4(b) Write an SQL query to display each student name with the titles "
        "of courses in which the student is enrolled."
    )


def test_strip_marks_annotations_removes_badge_at_end_and_preserves_technical_number() -> None:
    from app.services.extraction.line_classification import strip_marks_annotations

    source = "Perform the calculation in GF (19). (3 marks)"

    assert strip_marks_annotations(source) == "Perform the calculation in GF (19)."


def test_strip_marks_annotations_supports_points_and_arabic_labels() -> None:
    from app.services.extraction.line_classification import strip_marks_annotations

    assert strip_marks_annotations("Explain normalization. [2 points]") == "Explain normalization."
    assert strip_marks_annotations("اشرح التطبيع. (٢ درجتان)") == "اشرح التطبيع."
