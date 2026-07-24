"""Unit tests for the line-classification rules shared by the digital and
OCR extraction paths (app.services.extraction.line_classification). Pure
text-in, dataclass-out - no PDF or OCR involved, so these run instantly and
pin down the actual decision rules independently of either extraction path.
"""

from __future__ import annotations

from app.services.extraction.line_classification import LineKind, classify_line


def test_question_line_sets_kind_and_label_and_becomes_new_parent() -> None:
    result = classify_line("Q3. Short answer questions.", current_parent_label="Q1")

    assert result.kind is LineKind.QUESTION
    assert result.number_label == "Q3"
    assert result.marks is None


def test_question_line_with_inline_marks_extracts_value_and_matched_text() -> None:
    result = classify_line("Q1. Explain normalization. [5 marks]", current_parent_label=None)

    assert result.marks is not None
    assert result.marks.value == 5.0
    assert result.marks.matched_text == "[5 marks]"


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


def test_total_marks_line_is_classified() -> None:
    result = classify_line("Total Marks: 20", current_parent_label=None)

    assert result.kind is LineKind.TOTAL_MARKS


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
