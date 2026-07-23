"""Deterministic knowledge_base/manifest.json builder.

No timestamp is included in the manifest content, by design: task F allows
omitting it specifically so repeated generation against unchanged workbooks
always produces byte-for-byte identical output, which regression tests rely
on. json.dumps(..., sort_keys=True) plus sorted counters/aggregate hashing
make every field independent of in-memory processing order.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from app.services.knowledge_base.loader import RawWorkbook
from app.services.knowledge_base.models import NormalizedRecord
from app.services.knowledge_base.schemas import ALL_WORKBOOK_SCHEMAS

KB_NAME = "Exam Quality Knowledge Base"
KB_VERSION = "1.0"
GENERATION_SCHEMA_VERSION = "1.0"


def _aggregate_record_hash(records: list[NormalizedRecord]) -> str:
    ordered_hashes = sorted(r.record_hash for r in records)
    return hashlib.sha256("|".join(ordered_hashes).encode("utf-8")).hexdigest()


def build_manifest(
    source_dir: Path,
    raw_workbooks: dict[str, RawWorkbook],
    records: list[NormalizedRecord],
    validation_status: str,
) -> dict[str, object]:
    files = [
        {
            "name": schema.filename,
            "sha256": raw_workbooks[schema.filename].file_hash,
            "size_bytes": (source_dir / schema.filename).stat().st_size,
        }
        for schema in ALL_WORKBOOK_SCHEMAS
        if schema.filename in raw_workbooks
    ]

    record_counts_by_workbook = {
        schema.filename: sum(1 for r in records if r.source_workbook == schema.filename)
        for schema in ALL_WORKBOOK_SCHEMAS
    }
    record_counts_by_entity_type = dict(
        sorted(Counter(r.entity_type.value for r in records).items())
    )
    provenance_category_counts = dict(
        sorted(Counter(r.provenance_category.value for r in records).items())
    )

    return {
        "knowledge_base_name": KB_NAME,
        "version": KB_VERSION,
        "generation_schema_version": GENERATION_SCHEMA_VERSION,
        "status": validation_status,
        "files": files,
        "record_counts_by_workbook": record_counts_by_workbook,
        "record_counts_by_entity_type": record_counts_by_entity_type,
        "provenance_category_counts": provenance_category_counts,
        "total_normalized_records": len(records),
        "aggregate_record_hash": _aggregate_record_hash(records),
    }


def render_manifest(manifest: dict[str, object]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def write_manifest(manifest: dict[str, object], manifest_path: Path) -> None:
    manifest_path.write_text(render_manifest(manifest), encoding="utf-8")
