"""Confirms app.services.rules.identifiers still names real rows in the
approved KB workbooks. This is a focused existence/alignment check only -
not the general KB loading, validation, or normalization pipeline, which is
Milestone 7 scope."""

from __future__ import annotations

from pathlib import Path

import openpyxl

from app.services.rules.identifiers import MARKS_AND_TOTAL, NUMBERING

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_SOURCE = REPO_ROOT / "knowledge_base" / "source"


def _rows(filename: str) -> list[dict[str, object]]:
    workbook = openpyxl.load_workbook(KB_SOURCE / filename, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    header = rows[0]
    return [dict(zip(header, row, strict=False)) for row in rows[1:]]


def test_kb_source_files_exist() -> None:
    assert (KB_SOURCE / "04_requirements.xlsx").is_file()
    assert (KB_SOURCE / "07_evaluation_rules.xlsx").is_file()


def test_marks_and_total_requirement_id_exists_and_matches() -> None:
    requirements = _rows("04_requirements.xlsx")
    match = next(r for r in requirements if r["Requirement_ID"] == MARKS_AND_TOTAL.requirement_id)
    assert match["Dimension"] == "Marks and Totals"
    assert match["Requirement_Name"] == MARKS_AND_TOTAL.rule_name


def test_numbering_requirement_id_exists_and_matches() -> None:
    requirements = _rows("04_requirements.xlsx")
    match = next(r for r in requirements if r["Requirement_ID"] == NUMBERING.requirement_id)
    assert match["Dimension"] == "Numbering and Structure"
    assert match["Requirement_Name"] == NUMBERING.rule_name


def test_marks_and_total_rule_id_exists_and_matches() -> None:
    rules = _rows("07_evaluation_rules.xlsx")
    match = next(r for r in rules if r["Rule_ID"] == MARKS_AND_TOTAL.rule_id)
    assert match["Requirement_ID"] == MARKS_AND_TOTAL.requirement_id
    assert match["Rule_Name"] == MARKS_AND_TOTAL.rule_name


def test_numbering_rule_id_exists_and_matches() -> None:
    rules = _rows("07_evaluation_rules.xlsx")
    match = next(r for r in rules if r["Rule_ID"] == NUMBERING.rule_id)
    assert match["Requirement_ID"] == NUMBERING.requirement_id
    assert match["Rule_Name"] == NUMBERING.rule_name


def test_numbering_rule_output_statuses_exclude_not_applicable() -> None:
    # RULE019's own Output_Statuses column omits Not Applicable - the
    # numbering rule must never be able to reach that status.
    rules = _rows("07_evaluation_rules.xlsx")
    match = next(r for r in rules if r["Rule_ID"] == NUMBERING.rule_id)
    statuses = str(match["Output_Statuses"])
    assert "Not Applicable" not in statuses


def test_marks_and_total_rule_output_statuses_include_all_five() -> None:
    rules = _rows("07_evaluation_rules.xlsx")
    match = next(r for r in rules if r["Rule_ID"] == MARKS_AND_TOTAL.rule_id)
    statuses = str(match["Output_Statuses"])
    for expected in (
        "Satisfied",
        "Partially Satisfied",
        "Not Satisfied",
        "Not Verified",
        "Not Applicable",
    ):
        assert expected in statuses
