from __future__ import annotations

from pathlib import Path

import pytest
from kb_fixtures import VALID_ROWS, build_valid_kb, write_kb

from app.services.knowledge_base.models import KnowledgeBaseValidationError
from app.services.knowledge_base.schemas import ALL_WORKBOOK_SCHEMAS
from app.services.knowledge_base.validator import load_and_validate

REAL_KB_SOURCE = Path(__file__).resolve().parents[2] / "knowledge_base" / "source"


def _copy_rows(filename: str) -> list[dict[str, object]]:
    return [dict(row) for row in VALID_ROWS[filename]]


# --- Positive -----------------------------------------------------------


def test_valid_minimal_kb_passes(tmp_path: Path) -> None:
    dest = build_valid_kb(tmp_path)
    raw_workbooks = load_and_validate(dest)
    assert set(raw_workbooks) == {s.filename for s in ALL_WORKBOOK_SCHEMAS}


def test_real_kb_passes_validation() -> None:
    raw_workbooks = load_and_validate(REAL_KB_SOURCE)
    assert len(raw_workbooks) == 11


# --- Negative: missing workbook ------------------------------------------


def test_missing_workbook_fails(tmp_path: Path) -> None:
    dest = write_kb(tmp_path, omit_files=("05_evidence_types.xlsx",))
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any("05_evidence_types.xlsx" in issue.workbook for issue in excinfo.value.issues)


# --- Negative: missing required column -----------------------------------


def test_missing_required_column_fails(tmp_path: Path) -> None:
    header_without_dimension = [
        c for c in VALID_ROWS["04_requirements.xlsx"][0] if c != "Dimension"
    ]
    dest = write_kb(tmp_path, headers_by_file={"04_requirements.xlsx": header_without_dimension})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        issue.workbook == "04_requirements.xlsx" and issue.field == "Dimension"
        for issue in excinfo.value.issues
    )


# --- Negative: duplicate primary ID ---------------------------------------


def test_duplicate_primary_id_fails(tmp_path: Path) -> None:
    rows = _copy_rows("05_evidence_types.xlsx")
    duplicate = dict(rows[0])
    duplicate["Evidence_Name"] = "Duplicate row"
    rows.append(duplicate)  # same Evidence_Type_ID = EV001 twice
    dest = write_kb(tmp_path, rows_by_file={"05_evidence_types.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        "Duplicate primary ID" in issue.reason and issue.value == "EV001"
        for issue in excinfo.value.issues
    )


# --- Negative: blank mandatory ID -----------------------------------------


def test_blank_mandatory_id_fails(tmp_path: Path) -> None:
    rows = _copy_rows("05_evidence_types.xlsx")
    rows[0]["Evidence_Type_ID"] = ""
    dest = write_kb(tmp_path, rows_by_file={"05_evidence_types.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        issue.field == "Evidence_Type_ID" and "blank" in issue.reason.lower()
        for issue in excinfo.value.issues
    )


# --- Negative: dangling direct foreign key --------------------------------


def test_dangling_direct_foreign_key_fails(tmp_path: Path) -> None:
    rows = _copy_rows("06_evidence_mapping.xlsx")
    rows[0]["Requirement_ID"] = "REQ999"  # does not exist
    dest = write_kb(tmp_path, rows_by_file={"06_evidence_mapping.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        issue.workbook == "06_evidence_mapping.xlsx"
        and issue.field == "Requirement_ID"
        and issue.value == "REQ999"
        for issue in excinfo.value.issues
    )


# --- Negative: relationship errors -----------------------------------------


def test_unknown_relationship_from_id_fails(tmp_path: Path) -> None:
    rows = _copy_rows("09_relationships.xlsx")
    rows[0]["From_ID"] = "REF999"
    dest = write_kb(tmp_path, rows_by_file={"09_relationships.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        issue.workbook == "09_relationships.xlsx" and issue.field == "From_ID"
        for issue in excinfo.value.issues
    )


def test_unknown_relationship_to_id_fails(tmp_path: Path) -> None:
    rows = _copy_rows("09_relationships.xlsx")
    rows[0]["To_ID"] = "STD999"
    dest = write_kb(tmp_path, rows_by_file={"09_relationships.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        issue.workbook == "09_relationships.xlsx" and issue.field == "To_ID"
        for issue in excinfo.value.issues
    )


def test_relationship_entity_type_mismatch_fails(tmp_path: Path) -> None:
    rows = _copy_rows("09_relationships.xlsx")
    # REL003's From_ID (CRT001) is real, but declared as a Standard here -
    # a genuine type mismatch, not just an unknown ID.
    rows[2]["From_Entity_Type"] = "Standard"
    dest = write_kb(tmp_path, rows_by_file={"09_relationships.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        issue.workbook == "09_relationships.xlsx"
        and issue.field == "From_ID"
        and issue.value == "CRT001"
        for issue in excinfo.value.issues
    )


# --- Negative: invalid boolean-style value ---------------------------------


def test_invalid_boolean_value_fails(tmp_path: Path) -> None:
    rows = _copy_rows("01_references.xlsx")
    rows[0]["Official_Source"] = "Maybe"
    dest = write_kb(tmp_path, rows_by_file={"01_references.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        issue.field == "Official_Source" and issue.value == "Maybe"
        for issue in excinfo.value.issues
    )


def test_invalid_tristate_value_fails(tmp_path: Path) -> None:
    rows = _copy_rows("06_evidence_mapping.xlsx")
    rows[0]["Mandatory"] = "Sometimes"
    dest = write_kb(tmp_path, rows_by_file={"06_evidence_mapping.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        issue.field == "Mandatory" and issue.value == "Sometimes" for issue in excinfo.value.issues
    )


# --- Negative: invalid enum value ------------------------------------------


def test_invalid_enum_value_fails(tmp_path: Path) -> None:
    rows = _copy_rows("04_requirements.xlsx")
    rows[0]["Applicability"] = "Not a real applicability value"
    dest = write_kb(tmp_path, rows_by_file={"04_requirements.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(issue.field == "Applicability" for issue in excinfo.value.issues)


def test_invalid_list_enum_token_fails(tmp_path: Path) -> None:
    rows = _copy_rows("07_evaluation_rules.xlsx")
    rows[0]["Output_Statuses"] = "Satisfied; Extremely Satisfied"
    dest = write_kb(tmp_path, rows_by_file={"07_evaluation_rules.xlsx": rows})
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(issue.field == "Output_Statuses" for issue in excinfo.value.issues)


def test_all_issues_collected_not_just_first(tmp_path: Path) -> None:
    # Two independent, unrelated problems in two different workbooks -
    # both must be reported from a single validation run.
    ev_rows = _copy_rows("05_evidence_types.xlsx")
    ev_rows[0]["Evidence_Type_ID"] = ""
    ref_rows = _copy_rows("01_references.xlsx")
    ref_rows[0]["Official_Source"] = "Maybe"
    dest = write_kb(
        tmp_path,
        rows_by_file={"05_evidence_types.xlsx": ev_rows, "01_references.xlsx": ref_rows},
    )
    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    workbooks_with_issues = {issue.workbook for issue in excinfo.value.issues}
    assert "05_evidence_types.xlsx" in workbooks_with_issues
    assert "01_references.xlsx" in workbooks_with_issues
