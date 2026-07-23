from __future__ import annotations

from pathlib import Path

import pytest
from kb_fixtures import VALID_ROWS, write_kb

from app.services.knowledge_base.models import KnowledgeBaseValidationError, ProvenanceCategory
from app.services.knowledge_base.normalizer import normalize_all
from app.services.knowledge_base.provenance import classify_provenance
from app.services.knowledge_base.validator import load_and_validate

REAL_KB_SOURCE = Path(__file__).resolve().parents[2] / "knowledge_base" / "source"


def _real_records() -> list:
    raw = load_and_validate(REAL_KB_SOURCE)
    return normalize_all(raw)


def test_real_kb_every_row_maps_to_one_of_six_categories() -> None:
    records = _real_records()
    assert len(records) == 437
    valid_categories = set(ProvenanceCategory)
    assert all(r.provenance_category in valid_categories for r in records)


def test_real_kb_provenance_category_counts_match_all_six() -> None:
    # Empirically confirmed against the real KB workbooks this session.
    counts: dict[ProvenanceCategory, int] = {}
    for record in _real_records():
        counts[record.provenance_category] = counts.get(record.provenance_category, 0) + 1

    assert counts[ProvenanceCategory.OFFICIAL_REFERENCE] == 3
    assert counts[ProvenanceCategory.OFFICIAL_CRITERION] == 14
    assert counts[ProvenanceCategory.TEMPLATE_EVIDENCE] == 10
    assert counts[ProvenanceCategory.DERIVED_REQUIREMENT] == 23
    assert counts[ProvenanceCategory.SYSTEM_RULE] == 30
    assert counts[ProvenanceCategory.SYSTEM_POLICY] == 357
    assert sum(counts.values()) == 437


@pytest.mark.parametrize(
    ("official_id", "expected_category"),
    [
        ("REF001", ProvenanceCategory.OFFICIAL_REFERENCE),  # 01_references
        ("STD001", ProvenanceCategory.OFFICIAL_CRITERION),  # 02_standards, Official Standard
        ("STD008", ProvenanceCategory.TEMPLATE_EVIDENCE),  # 02_standards, Official Template Section
        ("CRT001", ProvenanceCategory.OFFICIAL_CRITERION),  # 03_criteria, Official
        (
            "CRT004",
            ProvenanceCategory.DERIVED_REQUIREMENT,
        ),  # 03_criteria, Derived from Official Standard
        ("CRT010", ProvenanceCategory.TEMPLATE_EVIDENCE),  # 03_criteria, Official Template Evidence
        ("CRT017", ProvenanceCategory.SYSTEM_POLICY),  # 03_criteria, System Defined
        ("REQ001", ProvenanceCategory.DERIVED_REQUIREMENT),  # 04_requirements, Derived
        ("REQ010", ProvenanceCategory.SYSTEM_POLICY),  # 04_requirements, System Defined
        ("EV001", ProvenanceCategory.SYSTEM_POLICY),  # 05_evidence_types
        ("MAP001", ProvenanceCategory.SYSTEM_POLICY),  # 06_evidence_mapping
        ("RULE001", ProvenanceCategory.SYSTEM_RULE),  # 07_evaluation_rules
        ("REC001", ProvenanceCategory.SYSTEM_POLICY),  # 08_recommendations
        ("REL001", ProvenanceCategory.SYSTEM_POLICY),  # 09_relationships
        ("META001", ProvenanceCategory.SYSTEM_POLICY),  # 10_metadata
        ("SCORE001", ProvenanceCategory.SYSTEM_POLICY),  # 11_scoring_policy
    ],
)
def test_representative_rows_map_to_expected_category(
    official_id: str, expected_category: ProvenanceCategory
) -> None:
    records = {r.official_id: r for r in _real_records()}
    assert records[official_id].provenance_category == expected_category


def test_unmappable_provenance_value_fails_validation_not_a_guess(tmp_path: Path) -> None:
    # Official_Source="No" passes the boolean-style column check (No is a
    # legitimate boolean value) but the provenance table only maps "Yes" for
    # this workbook - this must fail validation, never silently default to
    # a guessed category.
    rows = [dict(row) for row in VALID_ROWS["01_references.xlsx"]]
    rows[0]["Official_Source"] = "No"
    dest = write_kb(tmp_path, rows_by_file={"01_references.xlsx": rows})

    assert classify_provenance("01_references.xlsx", rows[0]) is None

    with pytest.raises(KnowledgeBaseValidationError) as excinfo:
        load_and_validate(dest)
    assert any(
        "provenance" in issue.reason.lower() and issue.workbook == "01_references.xlsx"
        for issue in excinfo.value.issues
    )
