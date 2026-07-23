from __future__ import annotations

from pathlib import Path

import pytest
from helpers import valid_pdf_bytes
from tp153_pdf_fixtures import (
    build_complete_tp153_pdf,
    build_incomplete_assessment_tp153_pdf,
    build_missing_clo_section_tp153_pdf,
)

from app.services.extraction.digital_tp153_extractor import PdfPlumberTp153Extractor
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


def test_unparseable_pdf_raises_extraction_error_without_leaking_details(tmp_path: Path) -> None:
    pdf_path = _write(tmp_path, "fake.pdf", valid_pdf_bytes())

    with pytest.raises(ExtractionError) as excinfo:
        PdfPlumberTp153Extractor().extract(pdf_path)

    assert "fake.pdf" in str(excinfo.value)
