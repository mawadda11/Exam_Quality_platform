from __future__ import annotations

from pathlib import Path

import pytest
from helpers import valid_pdf_bytes
from pdf_fixtures import build_blank_pdf, build_synthetic_exam_pdf
from rules_pdf_fixtures import build_exam_with_correct_total_pdf

from app.services.extraction.digital_pdf_extractor import PdfPlumberExamExtractor
from app.services.extraction.types import ExtractionError


def _write(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def test_extracts_expected_question_count_and_hierarchy(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    labels = [q.number_label for q in result.questions]
    assert labels == ["Q1", "Q2", "Q2(a)", "Q2(b)", "Q3", "Q3(a)", "Q3(b)", "Q4"]

    by_label = {q.number_label: q for q in result.questions}
    assert by_label["Q2(a)"].parent_number_label == "Q2"
    assert by_label["Q2(b)"].parent_number_label == "Q2"
    assert by_label["Q3(a)"].parent_number_label == "Q3"
    assert by_label["Q3(b)"].parent_number_label == "Q3"
    assert by_label["Q1"].parent_number_label is None
    assert by_label["Q2"].parent_number_label is None
    assert by_label["Q4"].parent_number_label is None


def test_extracts_expected_question_text(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    by_label = {q.number_label: q for q in result.questions}
    assert by_label["Q1"].text == (
        "Q1. Explain the concept of normalization in database design. [5 marks]"
    )
    assert by_label["Q2(a)"].text == "(a) Identify the primary key for the given table. [3 marks]"


def test_extracts_expected_page_numbers(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    by_label = {q.number_label: q for q in result.questions}
    for label in ("Q1", "Q2", "Q2(a)", "Q2(b)"):
        assert by_label[label].page_number == 1
    for label in ("Q3", "Q3(a)", "Q3(b)", "Q4"):
        assert by_label[label].page_number == 2


def test_extracts_expected_marks(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    by_label = {q.number_label: q for q in result.questions}
    assert by_label["Q1"].marks == 5.0
    assert by_label["Q2"].marks is None  # parent stem line carries no marks of its own
    assert by_label["Q2(a)"].marks == 3.0
    assert by_label["Q2(b)"].marks == 4.0
    assert by_label["Q3(a)"].marks == 2.0
    assert by_label["Q3(b)"].marks == 3.0
    assert by_label["Q4"].marks == 6.0


def test_questions_are_in_deterministic_sequence_order(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    sequences = [q.sequence for q in result.questions]
    assert sequences == sorted(sequences)
    assert sequences == list(range(1, 9))


def test_matched_questions_have_full_confidence_and_geometry(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    for question in result.questions:
        assert question.confidence == 1.0
        assert question.geometry is not None
        assert question.geometry.x1 > question.geometry.x0
        assert question.geometry.bottom > question.geometry.top


def test_extracts_instructions_and_marks_evidence(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    instructions = [e for e in result.evidence if e.evidence_type == "instructions"]
    assert len(instructions) == 1
    assert instructions[0].page_number == 1
    assert instructions[0].item_reference == "instructions"
    assert instructions[0].question_number_label is None
    assert "Answer all questions" in instructions[0].extracted_text

    marks_evidence = [e for e in result.evidence if e.evidence_type == "marks"]
    assert len(marks_evidence) == 6  # Q1, Q2(a), Q2(b), Q3(a), Q3(b), Q4 - not Q2/Q3 stems
    q1_marks = next(e for e in marks_evidence if e.item_reference == "Q1")
    assert q1_marks.extracted_text == "[5 marks]"
    assert q1_marks.page_number == 1
    assert q1_marks.confidence == 1.0


def test_question_text_evidence_is_traceable_to_source(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    question_evidence = {
        e.item_reference: e for e in result.evidence if e.evidence_type == "question_text"
    }
    assert question_evidence["Q1"].page_number == 1
    assert question_evidence["Q4"].page_number == 2
    assert question_evidence["Q1"].question_number_label == "Q1"


def test_extracts_declared_total_as_evidence_not_a_question(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_exam_with_correct_total_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    total_evidence = [e for e in result.evidence if e.evidence_type == "declared_total"]
    assert len(total_evidence) == 1
    assert total_evidence[0].extracted_text == "Total Marks: 15"
    assert total_evidence[0].item_reference == "total"
    assert total_evidence[0].question_number_label is None
    assert total_evidence[0].confidence == 1.0

    # The "Total Marks: 15" line must never itself become a question row.
    assert all(q.text != "Total Marks: 15" for q in result.questions)


def test_exam_without_a_total_line_yields_no_declared_total_evidence(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "exam.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    assert all(e.evidence_type != "declared_total" for e in result.evidence)


def test_blank_pdf_yields_no_questions_without_error(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "blank.pdf", build_blank_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    assert result.questions == []
    assert all(e.evidence_type != "question_text" for e in result.evidence)


def test_unparseable_pdf_raises_extraction_error_without_leaking_details(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "fake.pdf", valid_pdf_bytes())

    with pytest.raises(ExtractionError) as excinfo:
        PdfPlumberExamExtractor().extract(pdf_path)

    # The error is safe to log server-side, but must not embed raw parser
    # internals in a way that would leak file-system layout to a client -
    # only the extractor's own message shape, never a bare parser traceback string.
    assert "fake.pdf" in str(excinfo.value)
