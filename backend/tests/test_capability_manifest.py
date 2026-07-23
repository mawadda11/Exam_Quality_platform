"""Validates app.services.rules.capability_manifest: the source-controlled
record of which official KB rules the runtime rule engine actually
evaluates, introduced by the M8 correction so a missing evaluation
capability is never represented as an unconditional Not Verified Finding.
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
        assert by_id[entry.rule_id]["Rule_Name"] == entry.requirement_name


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
    assert unsupported, "expected at least one unsupported entry"
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


def test_rule002_and_rule008_are_unsupported() -> None:
    by_rule_id = {e.rule_id: e for e in CAPABILITY_MANIFEST}
    assert by_rule_id["RULE002"].support_status is SupportStatus.UNSUPPORTED
    assert by_rule_id["RULE008"].support_status is SupportStatus.UNSUPPORTED


def test_rule006_is_partially_supported_with_both_branches_documented() -> None:
    by_rule_id = {e.rule_id: e for e in CAPABILITY_MANIFEST}
    entry = by_rule_id["RULE006"]
    assert entry.support_status is SupportStatus.PARTIALLY_SUPPORTED
    assert entry.reason is not None
    lowered = entry.reason.lower()
    assert "one applicable clo" in lowered or "one CLO" in entry.reason
    assert "two or more" in lowered


# --- planned_milestone_or_dependency: optional, never invented ---------------


def test_planned_milestone_or_dependency_is_none_unless_explicitly_set() -> None:
    # No production entry currently names a planned milestone/dependency -
    # nothing in the repository's actual documentation (docs/IMPLEMENTATION_ROADMAP.md
    # or elsewhere) formally establishes a future milestone for REQ002/REQ008's
    # semantic-evaluation gap, so this field must not be populated by inference.
    for entry in CAPABILITY_MANIFEST:
        assert entry.planned_milestone_or_dependency is None


# --- Manifest population matches the approved M8-correction scope exactly ----


def test_manifest_contains_exactly_the_approved_nine_entries() -> None:
    by_status: dict[SupportStatus, set[str]] = {status: set() for status in SupportStatus}
    for entry in CAPABILITY_MANIFEST:
        by_status[entry.support_status].add(entry.rule_id)

    assert by_status[SupportStatus.SUPPORTED] == {
        "RULE001",
        "RULE005",
        "RULE007",
        "RULE009",
        "RULE018",
        "RULE019",
    }
    assert by_status[SupportStatus.PARTIALLY_SUPPORTED] == {"RULE006"}
    assert by_status[SupportStatus.UNSUPPORTED] == {"RULE002", "RULE008"}
    assert len(CAPABILITY_MANIFEST) == 9


# --- Schema flexibility for future (not-yet-implemented) gap categories -----
# Test-only instances, per the approved plan - never added to
# CAPABILITY_MANIFEST itself, and none of these represent an M9 decision.


def test_schema_can_represent_a_language_quality_gap() -> None:
    entry = CapabilityEntry(
        requirement_id="REQ011",
        rule_id="RULE011",
        requirement_name="Clear Task Statement",
        support_status=SupportStatus.UNSUPPORTED,
        reason="Requires judging wording clarity - a Language Rule with no deterministic proxy.",
    )
    assert entry.support_status is SupportStatus.UNSUPPORTED


def test_schema_can_represent_an_ocr_vision_gap() -> None:
    # planned_milestone_or_dependency is left None: no repository
    # documentation formally schedules OCR/vision support, so none is
    # invented here either - the schema must accept that state cleanly.
    entry = CapabilityEntry(
        requirement_id="REQ015",
        rule_id="RULE015",
        requirement_name="Supporting Material Legibility",
        support_status=SupportStatus.UNSUPPORTED,
        reason="Requires visual/OCR analysis, which this system does not perform.",
    )
    assert entry.planned_milestone_or_dependency is None


def test_schema_can_represent_an_institutional_configuration_gap() -> None:
    entry = CapabilityEntry(
        requirement_id="REQ020",
        rule_id="RULE020",
        requirement_name="Exam Identification",
        support_status=SupportStatus.UNSUPPORTED,
        reason=(
            "Requires an institutional policy of which metadata fields are required, which "
            "does not exist as a system concept."
        ),
    )
    assert entry.reason is not None


def test_schema_can_represent_a_meta_rule_that_does_not_belong_in_findings() -> None:
    entry = CapabilityEntry(
        requirement_id="REQ010",
        rule_id="RULE010",
        requirement_name="Finding Traceability",
        support_status=SupportStatus.UNSUPPORTED,
        reason=(
            "Validates other Findings' structure rather than exam content; already satisfied "
            "by construction (every Finding carries evidence links) and enforced by tests, "
            "not appropriate as a per-analysis Finding."
        ),
    )
    assert entry.support_status is SupportStatus.UNSUPPORTED
