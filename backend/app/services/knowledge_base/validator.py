"""Schema, identifier-registry, and relationship validation for the KB.

Two passes, both collecting every issue found (never stopping at the
first, never silently dropping a bad row):
1. Per-workbook: required columns present, required-non-empty fields,
   closed-value enums/booleans, unique primary IDs, provenance
   classification.
2. Cross-workbook: direct foreign-key-shaped columns resolve against the
   identifier registry built from pass 1's valid primary IDs; and
   09_relationships.xlsx's polymorphic From/To pairs resolve against the
   registry bucket matching their *declared* entity type specifically (so
   a real ID used under the wrong declared type is still an error).
"""

from __future__ import annotations

from pathlib import Path

from app.services.knowledge_base.entity_types import EntityType
from app.services.knowledge_base.loader import (
    KnowledgeBaseFileMissingError,
    RawRow,
    RawWorkbook,
    load_workbook,
)
from app.services.knowledge_base.models import KnowledgeBaseValidationError, ValidationIssue
from app.services.knowledge_base.provenance import classify_provenance
from app.services.knowledge_base.schemas import (
    ALL_WORKBOOK_SCHEMAS,
    REGISTRY_WORKBOOKS,
    RELATIONSHIPS,
    ColumnKind,
    ColumnSpec,
    WorkbookSchema,
)

Registry = dict[EntityType, set[str]]


def _is_blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def _validate_required_columns(raw: RawWorkbook, issues: list[ValidationIssue]) -> None:
    for column in raw.schema.columns:
        if column.name not in raw.header:
            issues.append(
                ValidationIssue(
                    workbook=raw.schema.filename,
                    sheet=raw.sheet,
                    row_number=None,
                    field=column.name,
                    value=None,
                    reason="Required column is missing from the workbook header.",
                )
            )


def _validate_column_value(column: ColumnSpec, row: RawRow, issues: list[ValidationIssue]) -> None:
    raw_value = row.values.get(column.name)
    blank = _is_blank(raw_value)

    if blank:
        if column.required:
            issues.append(
                ValidationIssue(
                    workbook=row.workbook,
                    sheet=row.sheet,
                    row_number=row.row_number,
                    field=column.name,
                    value=raw_value,
                    reason="Required field is blank.",
                )
            )
        return

    value = str(raw_value).strip()

    if column.kind in (ColumnKind.BOOLEAN, ColumnKind.BOOLEAN_TRISTATE, ColumnKind.ENUM):
        assert column.allowed_values is not None
        if value not in column.allowed_values:
            allowed = sorted(column.allowed_values)
            issues.append(
                ValidationIssue(
                    workbook=row.workbook,
                    sheet=row.sheet,
                    row_number=row.row_number,
                    field=column.name,
                    value=raw_value,
                    reason=f"Value is not one of the allowed values: {allowed}.",
                )
            )
    elif column.kind == ColumnKind.LIST_ENUM:
        assert column.allowed_values is not None
        tokens = [t.strip() for t in value.split(column.list_delimiter.strip()) if t.strip()]
        unknown = [t for t in tokens if t not in column.allowed_values]
        if not tokens or unknown:
            bad = unknown or "empty list"
            issues.append(
                ValidationIssue(
                    workbook=row.workbook,
                    sheet=row.sheet,
                    row_number=row.row_number,
                    field=column.name,
                    value=raw_value,
                    reason=f"List contains values outside the allowed set: {bad}.",
                )
            )


def _validate_primary_id_uniqueness(raw: RawWorkbook, issues: list[ValidationIssue]) -> None:
    seen: dict[str, int] = {}
    duplicates: set[str] = set()
    for row in raw.rows:
        raw_id = row.values.get(raw.schema.primary_id_column)
        if _is_blank(raw_id):
            continue
        key = str(raw_id).strip()
        if key in seen:
            duplicates.add(key)
        else:
            seen[key] = row.row_number

    if not duplicates:
        return
    for row in raw.rows:
        raw_id = row.values.get(raw.schema.primary_id_column)
        if _is_blank(raw_id):
            continue
        key = str(raw_id).strip()
        if key in duplicates:
            issues.append(
                ValidationIssue(
                    workbook=raw.schema.filename,
                    sheet=row.sheet,
                    row_number=row.row_number,
                    field=raw.schema.primary_id_column,
                    value=raw_id,
                    reason="Duplicate primary ID within this workbook.",
                )
            )


def _validate_provenance(raw: RawWorkbook, issues: list[ValidationIssue]) -> None:
    for row in raw.rows:
        if classify_provenance(raw.schema.filename, row.values) is None:
            issues.append(
                ValidationIssue(
                    workbook=raw.schema.filename,
                    sheet=row.sheet,
                    row_number=row.row_number,
                    field=None,
                    value=None,
                    reason="Row could not be reliably mapped to a provenance category.",
                )
            )


def _validate_workbook_shape(raw: RawWorkbook, issues: list[ValidationIssue]) -> None:
    _validate_required_columns(raw, issues)
    if any(c.name not in raw.header for c in raw.schema.columns):
        return  # Column-level checks below assume the header is intact.
    for row in raw.rows:
        for column in raw.schema.columns:
            _validate_column_value(column, row, issues)
    _validate_primary_id_uniqueness(raw, issues)
    _validate_provenance(raw, issues)


def _build_registry(raw_workbooks: dict[str, RawWorkbook]) -> Registry:
    registry: Registry = {entity_type: set() for entity_type in EntityType}
    for schema in REGISTRY_WORKBOOKS:
        raw = raw_workbooks.get(schema.filename)
        if raw is None:
            continue
        for row in raw.rows:
            raw_id = row.values.get(schema.primary_id_column)
            if not _is_blank(raw_id):
                registry[schema.entity_type].add(str(raw_id).strip())
    return registry


def _validate_foreign_keys(
    raw: RawWorkbook, registry: Registry, issues: list[ValidationIssue]
) -> None:
    for fk in raw.schema.foreign_keys:
        for row in raw.rows:
            raw_value = row.values.get(fk.column)
            if _is_blank(raw_value):
                continue  # A blank required FK column is already reported above.
            key = str(raw_value).strip()
            if key not in registry[fk.target_entity_type]:
                issues.append(
                    ValidationIssue(
                        workbook=raw.schema.filename,
                        sheet=row.sheet,
                        row_number=row.row_number,
                        field=fk.column,
                        value=raw_value,
                        reason=f"References an unknown {fk.target_entity_type.value} ID.",
                    )
                )


def _validate_relationships_workbook(
    raw: RawWorkbook, registry: Registry, issues: list[ValidationIssue]
) -> None:
    valid_types = {e.value for e in EntityType}
    for row in raw.rows:
        for prefix, type_field, id_field in (
            ("From", "From_Entity_Type", "From_ID"),
            ("To", "To_Entity_Type", "To_ID"),
        ):
            type_raw = row.values.get(type_field)
            id_raw = row.values.get(id_field)
            if _is_blank(type_raw) or _is_blank(id_raw):
                continue  # Blank required fields are already reported above.

            type_value = str(type_raw).strip()
            id_value = str(id_raw).strip()
            if type_value not in valid_types:
                issues.append(
                    ValidationIssue(
                        workbook=raw.schema.filename,
                        sheet=row.sheet,
                        row_number=row.row_number,
                        field=type_field,
                        value=type_raw,
                        reason="Not a known KB entity type.",
                    )
                )
                continue

            entity_type = EntityType(type_value)
            if id_value not in registry[entity_type]:
                issues.append(
                    ValidationIssue(
                        workbook=raw.schema.filename,
                        sheet=row.sheet,
                        row_number=row.row_number,
                        field=id_field,
                        value=id_raw,
                        reason=(
                            f"{prefix}_ID does not resolve to a known {entity_type.value} ID "
                            "(unknown ID, or it belongs to a different declared entity type)."
                        ),
                    )
                )


def load_and_validate(
    source_dir: Path, schemas: tuple[WorkbookSchema, ...] = ALL_WORKBOOK_SCHEMAS
) -> dict[str, RawWorkbook]:
    """Loads and fully validates every workbook. Returns the raw workbooks
    keyed by filename on success; raises KnowledgeBaseValidationError with
    every collected issue otherwise. Never silently drops a bad row."""
    issues: list[ValidationIssue] = []
    raw_workbooks: dict[str, RawWorkbook] = {}

    for schema in schemas:
        try:
            raw_workbooks[schema.filename] = load_workbook(source_dir, schema)
        except KnowledgeBaseFileMissingError as exc:
            issues.append(
                ValidationIssue(
                    workbook=schema.filename,
                    sheet=None,
                    row_number=None,
                    field=None,
                    value=None,
                    reason=str(exc),
                )
            )

    for raw in raw_workbooks.values():
        _validate_workbook_shape(raw, issues)

    registry = _build_registry(raw_workbooks)

    for raw in raw_workbooks.values():
        if raw.schema.foreign_keys:
            _validate_foreign_keys(raw, registry, issues)
        if raw.schema.filename == RELATIONSHIPS.filename:
            _validate_relationships_workbook(raw, registry, issues)

    if issues:
        raise KnowledgeBaseValidationError(issues)
    return raw_workbooks
