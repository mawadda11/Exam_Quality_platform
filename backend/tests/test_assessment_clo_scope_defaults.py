from types import SimpleNamespace

from app.core.domain import ExamType
from app.services.extraction.digital_tp153_extractor import (
    AdaptiveCourseSpecificationExtractor,
    CourseSpecificationLine,
    _header_role,
    _table_section,
)
from app.services.rules.assessment_applicability import resolve_applicable_clo_codes


def test_alignment_matrix_headers_are_recognized() -> None:
    roles = tuple(
        _header_role(value)
        for value in ("Assessment Activity", "CLO1", "CLO2", "CLO3", "CLO4")
    )
    assert roles == ("method", "clo:CLO1", "clo:CLO2", "clo:CLO3", "clo:CLO4")
    assert _table_section(roles) == "assessment_records"


def test_alignment_matrix_row_extracts_only_marked_clos() -> None:
    extractor = AdaptiveCourseSpecificationExtractor()
    row = CourseSpecificationLine(
        text="Final Examination | X | ✓ | 1 | -",
        page_number=3,
        raw_cells=("Final Examination", "X", "✓", "1", "-"),
        reading_cells=("Final Examination", "X", "✓", "1", "-"),
        cell_roles=("method", "clo:CLO1", "clo:CLO2", "clo:CLO3", "clo:CLO4"),
        table_section="assessment_records",
    )
    record = extractor._parse_structured_assessment(row)
    assert record is not None
    assert record.method == "Final Examination"
    assert record.related_clo_codes == ("CLO1", "CLO2", "CLO3")


def test_inline_assessment_mapping_is_extracted_without_weight() -> None:
    extractor = AdaptiveCourseSpecificationExtractor()
    line = CourseSpecificationLine(
        text="Final Examination CLO1, CLO2, CLO3",
        page_number=3,
    )
    records = extractor._parse_assessments(line, [], "assessment_records")
    assert len(records) == 1
    assert records[0].method == "Final Examination"
    assert records[0].percentage is None
    assert records[0].related_clo_codes == ("CLO1", "CLO2", "CLO3")


def test_missing_exam_specific_mapping_preserves_all_clos_fallback() -> None:
    records = [SimpleNamespace(method="Project", related_clo_codes=["CLO4"])]
    assert (
        resolve_applicable_clo_codes(
            ExamType.FINAL,
            records,
            ["CLO1", "CLO2", "CLO3", "CLO4"],
        )
        is None
    )
