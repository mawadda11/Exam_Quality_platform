from __future__ import annotations

from pathlib import Path

from kb_fixtures import build_valid_kb

from app.services.knowledge_base.manifest import build_manifest, render_manifest
from app.services.knowledge_base.normalizer import normalize_all
from app.services.knowledge_base.validator import load_and_validate

REAL_KB_SOURCE = Path(__file__).resolve().parents[2] / "knowledge_base" / "source"


def _manifest_for(source_dir: Path) -> dict[str, object]:
    raw = load_and_validate(source_dir)
    records = normalize_all(raw)
    return build_manifest(source_dir, raw, records, validation_status="valid")


def test_manifest_has_expected_top_level_fields(tmp_path: Path) -> None:
    dest = build_valid_kb(tmp_path)
    manifest = _manifest_for(dest)
    expected_keys = {
        "knowledge_base_name",
        "version",
        "generation_schema_version",
        "status",
        "files",
        "record_counts_by_workbook",
        "record_counts_by_entity_type",
        "provenance_category_counts",
        "total_normalized_records",
        "aggregate_record_hash",
    }
    assert expected_keys <= set(manifest)
    assert len(manifest["files"]) == 11
    for file_entry in manifest["files"]:
        assert {"name", "sha256", "size_bytes"} <= set(file_entry)


def test_manifest_has_no_timestamp_field(tmp_path: Path) -> None:
    dest = build_valid_kb(tmp_path)
    manifest = _manifest_for(dest)
    for key in manifest:
        assert "time" not in key.lower() and "date" not in key.lower()


def test_manifest_generation_is_byte_for_byte_deterministic(tmp_path: Path) -> None:
    dest = build_valid_kb(tmp_path)
    first = render_manifest(_manifest_for(dest))
    second = render_manifest(_manifest_for(dest))
    assert first == second


def test_real_kb_manifest_counts_match_known_totals() -> None:
    manifest = _manifest_for(REAL_KB_SOURCE)
    assert manifest["total_normalized_records"] == 437
    assert manifest["status"] == "valid"
    assert sum(manifest["record_counts_by_workbook"].values()) == 437
    assert sum(manifest["provenance_category_counts"].values()) == 437
    assert manifest["provenance_category_counts"]["system rule"] == 30
    assert manifest["provenance_category_counts"]["official reference"] == 3


def test_real_kb_manifest_is_deterministic_across_runs() -> None:
    first = render_manifest(_manifest_for(REAL_KB_SOURCE))
    second = render_manifest(_manifest_for(REAL_KB_SOURCE))
    assert first == second
