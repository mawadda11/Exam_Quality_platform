"""Validates the complete exam-facing Version 1 capability scope.

Implemented entries must match the real runtime. Retained and explicitly
deferred gaps must remain documented as unsupported until their approved
dependencies are implemented; a missing capability is never represented as
an unconditional Not Verified Finding.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from app.services.processing.stages import RUNTIME_RULE_IDENTIFIERS
from app.services.rules.capability_manifest import (
    CAPABILITY_MANIFEST,
    CapabilityEntry,
    SupportStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_SOURCE = REPO_ROOT / "knowledge_base" / "source"


def _rows(filename: str) -> list[dict[str, object]]:
    workbook = openpyxl.load_workbook(KB_SOURCE / filename, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    header = rows[0]
    return [dict(zip(header, row, strict=False)) for row in rows[1:]]


# --- SupportStatus shape -----------------------------------------------------


def test_support_status_has_exactly_three_members() -> None:
    assert {member.value for member in SupportStatus} == {
        "supported",
        "partially_supported",
        "unsupported",
    }


# --- Official ID alignment against the real KB -------------------------------


def test_every_manifest_requirement_id_exists_in_kb_and_matches_name() -> None:
    requirements = _rows("04_requirements.xlsx")
    by_id = {r["Requirement_ID"]: r for r in requirements}
    for entry in CAPABILITY_MANIFEST:
        assert entry.requirement_id in by_id, f"{entry.requirement_id} not found in KB"
        assert by_id[entry.requirement_id]["Requirement_Name"] == entry.requirement_name


def test_every_manifest_rule_id_exists_in_kb_and_matches_requirement() -> None:
    rules = _rows("07_evaluation_rules.xlsx")
    by_id = {r["Rule_ID"]: r for r in rules}
    for entry in CAPABILITY_MANIFEST:
        assert entry.rule_id in by_id, f"{entry.rule_id} not found in KB"
        assert by_id[entry.rule_id]["Requirement_ID"] == entry.requirement_id
        assert by_id[entry.rule_id]["Rule_Name"] == entry.effective_rule_name


# --- Uniqueness ---------------------------------------------------------------


def test_no_duplicate_requirement_ids() -> None:
    ids = [entry.requirement_id for entry in CAPABILITY_MANIFEST]
    assert len(ids) == len(set(ids))


def test_no_duplicate_rule_ids() -> None:
    ids = [entry.rule_id for entry in CAPABILITY_MANIFEST]
    assert len(ids) == len(set(ids))


# --- Reason/scope-description requirements -----------------------------------


def test_unsupported_entries_have_a_non_empty_reason() -> None:
    unsupported = [e for e in CAPABILITY_MANIFEST if e.support_status is SupportStatus.UNSUPPORTED]
    for entry in unsupported:
        assert entry.reason is not None and entry.reason.strip()


def test_partially_supported_entries_have_a_non_empty_scope_description() -> None:
    partial = [
        e for e in CAPABILITY_MANIFEST if e.support_status is SupportStatus.PARTIALLY_SUPPORTED
    ]
    assert partial, "expected at least one partially supported entry"
    for entry in partial:
        assert entry.reason is not None and entry.reason.strip()


def test_capability_entry_rejects_unsupported_without_reason() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        CapabilityEntry(
            requirement_id="REQ999",
            rule_id="RULE999",
            requirement_name="Test",
            support_status=SupportStatus.UNSUPPORTED,
        )


def test_capability_entry_rejects_partially_supported_without_reason() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        CapabilityEntry(
            requirement_id="REQ999",
            rule_id="RULE999",
            requirement_name="Test",
            support_status=SupportStatus.PARTIALLY_SUPPORTED,
        )


def test_capability_entry_allows_supported_without_reason() -> None:
    entry = CapabilityEntry(
        requirement_id="REQ999",
        rule_id="RULE999",
        requirement_name="Test",
        support_status=SupportStatus.SUPPORTED,
    )
    assert entry.reason is None


# --- Correspondence with the real runtime pipeline ----------------------------


def test_supported_and_partially_supported_entries_match_runtime_rule_identifiers() -> None:
    manifest_runtime_ids = {
        e.rule_id
        for e in CAPABILITY_MANIFEST
        if e.support_status in (SupportStatus.SUPPORTED, SupportStatus.PARTIALLY_SUPPORTED)
    }
    actual_runtime_ids = {identifier.rule_id for identifier in RUNTIME_RULE_IDENTIFIERS}
    assert manifest_runtime_ids == actual_runtime_ids


def test_unsupported_entries_are_not_in_runtime_rule_identifiers() -> None:
    unsupported_ids = {
        e.rule_id for e in CAPABILITY_MANIFEST if e.support_status is SupportStatus.UNSUPPORTED
    }
    actual_runtime_ids = {identifier.rule_id for identifier in RUNTIME_RULE_IDENTIFIERS}
    assert unsupported_ids.isdisjoint(actual_runtime_ids)


def test_approved_semantic_rules_are_supported() -> None:
    by_rule_id = {e.rule_id: e for e in CAPABILITY_MANIFEST}
    for rule_id in ("RULE002", "RULE004", "RULE008"):
        entry = by_rule_id[rule_id]
        assert entry.support_status is SupportStatus.SUPPORTED
        assert entry.implemented_milestone == "Semantic AI/RAG"


def test_rule006_is_partially_supported_with_both_branches_documented() -> None:
    by_rule_id = {e.rule_id: e for e in CAPABILITY_MANIFEST}
    entry = by_rule_id["RULE006"]
    assert entry.support_status is SupportStatus.PARTIALLY_SUPPORTED
    assert entry.reason is not None
    lowered = entry.reason.lower()
    assert "one applicable clo" in lowered or "one CLO" in entry.reason
    assert "two or more" in lowered


# --- Approved retained and deferred Version 1 scope --------------------------


def test_only_approved_retained_rules_name_a_v1_implementation_dependency() -> None:
    planned = {
        entry.rule_id
        for entry in CAPABILITY_MANIFEST
        if entry.planned_milestone_or_dependency is not None
    }
    assert planned == {
        "RULE003",
        "RULE011",
        "RULE012",
        "RULE013",
        "RULE014",
        "RULE016",
        "RULE021",
        "RULE022",
    }


def test_criteria_blocked_rules_remain_explicitly_deferred() -> None:
    by_rule_id = {entry.rule_id: entry for entry in CAPABILITY_MANIFEST}
    assert {
        rule_id
        for rule_id in ("RULE015", "RULE017", "RULE020")
        if by_rule_id[rule_id].support_status is SupportStatus.UNSUPPORTED
        and by_rule_id[rule_id].planned_milestone_or_dependency is None
    } == {"RULE015", "RULE017", "RULE020"}

    assert "threshold" in (by_rule_id["RULE015"].reason or "").lower()
    assert "institutional" in (by_rule_id["RULE017"].reason or "").lower()
    assert "institutional" in (by_rule_id["RULE020"].reason or "").lower()


# --- Manifest population covers every exam-facing KB rule -------------------


def test_manifest_contains_every_exam_facing_rule_with_frozen_status() -> None:
    by_status: dict[SupportStatus, set[str]] = {status: set() for status in SupportStatus}
    for entry in CAPABILITY_MANIFEST:
        by_status[entry.support_status].add(entry.rule_id)

    assert by_status[SupportStatus.SUPPORTED] == {
        "RULE001",
        "RULE002",
        "RULE004",
        "RULE005",
        "RULE007",
        "RULE008",
        "RULE009",
        "RULE018",
        "RULE019",
    }
    assert by_status[SupportStatus.PARTIALLY_SUPPORTED] == {"RULE006"}
    assert by_status[SupportStatus.UNSUPPORTED] == {
        "RULE003",
        "RULE011",
        "RULE012",
        "RULE013",
        "RULE014",
        "RULE015",
        "RULE016",
        "RULE017",
        "RULE020",
        "RULE021",
        "RULE022",
    }
    assert len(CAPABILITY_MANIFEST) == 21

    requirements = _rows("04_requirements.xlsx")
    exam_facing_requirement_ids = {
        str(row["Requirement_ID"])
        for row in requirements
        if row["Source_Type"] == "Derived Exam Requirement"
    }
    assert {entry.requirement_id for entry in CAPABILITY_MANIFEST} == exam_facing_requirement_ids
