"""Converts already-validated RawWorkbook rows into typed NormalizedRecord
instances. Assumes load_and_validate() has already run and raised on any
problem - this module does not re-validate, it only standardizes and hashes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from app.services.knowledge_base.loader import RawWorkbook
from app.services.knowledge_base.models import NormalizedRecord, ProvenanceCategory
from app.services.knowledge_base.provenance import classify_provenance
from app.services.knowledge_base.schemas import ColumnKind, ColumnSpec

_NULL_TOKENS = {"", "None"}


def _normalize_value(column: ColumnSpec, raw_value: object) -> object:
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if text in _NULL_TOKENS:
        return None
    if column.kind == ColumnKind.BOOLEAN:
        return text == "Yes"
    if column.kind == ColumnKind.LIST_ENUM:
        return [t.strip() for t in text.split(column.list_delimiter.strip()) if t.strip()]
    return text


def compute_record_hash(
    entity_type_value: str,
    official_id: str,
    provenance_category: ProvenanceCategory,
    data: Mapping[str, object],
) -> str:
    """Deterministic regardless of dict insertion order - keys are sorted
    before hashing, and every value is passed through repr() so type
    (None vs "None", bool vs "True") is part of the hashed content."""
    canonical = "|".join(f"{key}={data[key]!r}" for key in sorted(data))
    payload = f"{entity_type_value}|{official_id}|{provenance_category.value}|{canonical}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_workbook(raw: RawWorkbook) -> list[NormalizedRecord]:
    records: list[NormalizedRecord] = []
    for row in raw.rows:
        official_id = str(row.values.get(raw.schema.primary_id_column)).strip()
        data = {
            column.name: _normalize_value(column, row.values.get(column.name))
            for column in raw.schema.columns
            if column.name != raw.schema.primary_id_column
        }
        provenance = classify_provenance(raw.schema.filename, row.values)
        if provenance is None:
            raise AssertionError(
                f"{raw.schema.filename} row {row.row_number}: unmapped provenance reached "
                "normalize_workbook() - load_and_validate() should have rejected this row."
            )
        record_hash = compute_record_hash(
            raw.schema.entity_type.value, official_id, provenance, data
        )
        records.append(
            NormalizedRecord(
                entity_type=raw.schema.entity_type,
                official_id=official_id,
                data=data,
                provenance_category=provenance,
                source_workbook=raw.schema.filename,
                source_sheet=raw.sheet,
                source_row_number=row.row_number,
                source_file_hash=raw.file_hash,
                record_hash=record_hash,
            )
        )
    return records


def normalize_all(raw_workbooks: Mapping[str, RawWorkbook]) -> list[NormalizedRecord]:
    """Deterministic order: raw_workbooks is built by load_and_validate() by
    iterating schemas in the fixed 01-11 order, and each workbook's rows are
    already in source-row order."""
    records: list[NormalizedRecord] = []
    for raw in raw_workbooks.values():
        records.extend(normalize_workbook(raw))
    return records
