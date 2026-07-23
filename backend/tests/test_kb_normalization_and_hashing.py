from __future__ import annotations

from pathlib import Path

from kb_fixtures import VALID_ROWS, build_valid_kb, write_kb

from app.services.knowledge_base.models import ProvenanceCategory
from app.services.knowledge_base.normalizer import compute_record_hash, normalize_all
from app.services.knowledge_base.validator import load_and_validate

REAL_KB_SOURCE = Path(__file__).resolve().parents[2] / "knowledge_base" / "source"


def test_official_ids_remain_unchanged(tmp_path: Path) -> None:
    dest = build_valid_kb(tmp_path)
    records = normalize_all(load_and_validate(dest))
    official_ids = {r.official_id for r in records}
    assert official_ids == {
        "REF001",
        "STD001",
        "CRT001",
        "REQ001",
        "EV001",
        "MAP001",
        "RULE001",
        "REC001",
        "META001",
        "SCORE001",
        "REL001",
        "REL002",
        "REL003",
        "REL004",
        "REL005",
        "REL006",
    }


def test_real_kb_official_ids_are_unchanged_sample() -> None:
    records = {r.official_id: r for r in normalize_all(load_and_validate(REAL_KB_SOURCE))}
    assert "REQ018" in records
    assert records["REQ018"].data["Requirement_Name"] == "Correct Total Marks"
    assert "RULE019" in records
    assert records["RULE019"].data["Rule_Name"] == "Consistent Numbering"


def test_whitespace_is_trimmed(tmp_path: Path) -> None:
    rows = [dict(row) for row in VALID_ROWS["05_evidence_types.xlsx"]]
    rows[0]["Evidence_Name"] = "  Padded Name  "
    dest = write_kb(tmp_path, rows_by_file={"05_evidence_types.xlsx": rows})
    records = {r.official_id: r for r in normalize_all(load_and_validate(dest))}
    assert records["EV001"].data["Evidence_Name"] == "Padded Name"


def test_literal_none_string_normalizes_to_python_none(tmp_path: Path) -> None:
    dest = build_valid_kb(tmp_path)
    records = {r.official_id: r for r in normalize_all(load_and_validate(dest))}
    assert records["REQ001"].data["Not_Applicable_Condition"] is None


def test_boolean_column_normalizes_to_python_bool(tmp_path: Path) -> None:
    dest = build_valid_kb(tmp_path)
    records = {r.official_id: r for r in normalize_all(load_and_validate(dest))}
    assert records["REF001"].data["Official_Source"] is True


def test_list_enum_column_normalizes_to_list(tmp_path: Path) -> None:
    dest = build_valid_kb(tmp_path)
    records = {r.official_id: r for r in normalize_all(load_and_validate(dest))}
    assert records["RULE001"].data["Output_Statuses"] == [
        "Satisfied",
        "Not Satisfied",
        "Not Verified",
    ]


def test_record_hash_is_deterministic_regardless_of_dict_order() -> None:
    data_a = {"x": "1", "y": "2"}
    data_b = {"y": "2", "x": "1"}
    hash_a = compute_record_hash(
        "Requirement", "REQ001", ProvenanceCategory.DERIVED_REQUIREMENT, data_a
    )
    hash_b = compute_record_hash(
        "Requirement", "REQ001", ProvenanceCategory.DERIVED_REQUIREMENT, data_b
    )
    assert hash_a == hash_b


def test_record_hash_changes_when_data_changes() -> None:
    base = compute_record_hash(
        "Requirement", "REQ001", ProvenanceCategory.DERIVED_REQUIREMENT, {"x": "1"}
    )
    changed = compute_record_hash(
        "Requirement", "REQ001", ProvenanceCategory.DERIVED_REQUIREMENT, {"x": "2"}
    )
    assert base != changed


def test_record_hash_changes_when_official_id_changes() -> None:
    first = compute_record_hash(
        "Requirement", "REQ001", ProvenanceCategory.DERIVED_REQUIREMENT, {"x": "1"}
    )
    second = compute_record_hash(
        "Requirement", "REQ002", ProvenanceCategory.DERIVED_REQUIREMENT, {"x": "1"}
    )
    assert first != second


def test_real_kb_all_rows_normalize_with_nonempty_hashes() -> None:
    records = normalize_all(load_and_validate(REAL_KB_SOURCE))
    assert len(records) == 437
    assert all(r.record_hash for r in records)
    # Every record's hash is unique - no two distinct rows collided.
    assert len({r.record_hash for r in records}) == 437


def test_normalize_all_is_deterministic_across_runs() -> None:
    first = normalize_all(load_and_validate(REAL_KB_SOURCE))
    second = normalize_all(load_and_validate(REAL_KB_SOURCE))
    assert [r.record_hash for r in first] == [r.record_hash for r in second]
