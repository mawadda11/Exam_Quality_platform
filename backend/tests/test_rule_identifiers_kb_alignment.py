"""Confirms app.services.rules.identifiers still names real rows in the
approved KB workbooks. This is a focused existence/alignment check only -
not the general KB loading, validation, or normalization pipeline, which is
Milestone 7 scope."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from app.services.rules.identifiers import (
    APPLICABLE_CLO_COVERAGE,
    APPLICABLE_TOPIC_COVERAGE,
    CLO_COVERAGE_DISTRIBUTION,
    MARKS_AND_TOTAL,
    NUMBERING,
    QUESTION_TO_CLO_MAPPING,
    QUESTION_TO_TOPIC_ALIGNMENT,
    RuleIdentifier,
)

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


# --- M8: CLO/topic alignment and coverage identifiers -----------------------


@pytest.mark.parametrize(
    ("identifier", "expected_dimension"),
    [
        (QUESTION_TO_CLO_MAPPING, "CLO Alignment"),
        (APPLICABLE_CLO_COVERAGE, "CLO Coverage"),
        (CLO_COVERAGE_DISTRIBUTION, "CLO Coverage"),
        (QUESTION_TO_TOPIC_ALIGNMENT, "Topic Alignment"),
        (APPLICABLE_TOPIC_COVERAGE, "Topic Coverage"),
    ],
)
def test_m8_requirement_id_exists_and_matches(
    identifier: RuleIdentifier, expected_dimension: str
) -> None:
    requirements = _rows("04_requirements.xlsx")
    match = next(r for r in requirements if r["Requirement_ID"] == identifier.requirement_id)
    assert match["Dimension"] == expected_dimension
    assert match["Requirement_Name"] == identifier.rule_name


@pytest.mark.parametrize(
    "identifier",
    [
        QUESTION_TO_CLO_MAPPING,
        APPLICABLE_CLO_COVERAGE,
        CLO_COVERAGE_DISTRIBUTION,
        QUESTION_TO_TOPIC_ALIGNMENT,
        APPLICABLE_TOPIC_COVERAGE,
    ],
)
def test_m8_rule_id_exists_and_matches(identifier: RuleIdentifier) -> None:
    rules = _rows("07_evaluation_rules.xlsx")
    match = next(r for r in rules if r["Rule_ID"] == identifier.rule_id)
    assert match["Requirement_ID"] == identifier.requirement_id
    assert match["Rule_Name"] == identifier.rule_name


def test_m8_alignment_rules_never_output_not_applicable() -> None:
    # REQ001/RULE001 and REQ007/RULE007 both declare Not_Applicable_Condition
    # "None" - our evaluators must never be able to reach that status.
    rules = _rows("07_evaluation_rules.xlsx")
    for identifier in (QUESTION_TO_CLO_MAPPING, QUESTION_TO_TOPIC_ALIGNMENT):
        match = next(r for r in rules if r["Rule_ID"] == identifier.rule_id)
        assert "Not Applicable" not in str(match["Output_Statuses"])


def test_clo_coverage_rule_never_outputs_not_applicable() -> None:
    rules = _rows("07_evaluation_rules.xlsx")
    match = next(r for r in rules if r["Rule_ID"] == APPLICABLE_CLO_COVERAGE.rule_id)
    assert "Not Applicable" not in str(match["Output_Statuses"])


def test_topic_coverage_rule_output_statuses_include_not_applicable() -> None:
    # RULE009 is the one M8 rule whose KB row *does* declare a real
    # Not_Applicable_Condition ("No topic set is designated...").
    rules = _rows("07_evaluation_rules.xlsx")
    match = next(r for r in rules if r["Rule_ID"] == APPLICABLE_TOPIC_COVERAGE.rule_id)
    assert "Not Applicable" in str(match["Output_Statuses"])


# --- M8 correction: RULE006's KB-literal Not Applicable condition -----------


def test_clo_coverage_distribution_not_applicable_condition_is_single_clo() -> None:
    # The one KB-defined, reachable-without-invented-logic Not_Applicable
    # condition among the three semantic-deferred rules.
    rules = _rows("07_evaluation_rules.xlsx")
    match = next(r for r in rules if r["Rule_ID"] == CLO_COVERAGE_DISTRIBUTION.rule_id)
    assert match["Not_Applicable_Condition"] == "Only one CLO is applicable."
    assert "Not Applicable" in str(match["Output_Statuses"])
