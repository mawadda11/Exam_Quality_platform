"""Reviewed, deterministic text projection for semantic KB retrieval."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.services.knowledge_base.entity_types import EntityType
from app.services.knowledge_base.models import NormalizedRecord
from app.services.knowledge_base.vector_store import EmbeddableRecord

_EMBEDDED_FIELDS: Mapping[EntityType, tuple[str, ...]] = {
    EntityType.REFERENCE: (
        "Reference_Code",
        "Reference_Name",
        "Organization",
        "Role_in_Knowledge_Base",
        "Scope_Use",
        "Notes",
    ),
    EntityType.STANDARD: (
        "Official_Code",
        "Standard_Name",
        "Record_Type",
        "Evaluation_Use",
        "Inclusion_Reason",
        "Scope_Limit",
    ),
    EntityType.CRITERION: (
        "Criterion_Code",
        "Criterion_Name",
        "Source_Type",
        "Officiality",
        "Evidence_Source",
        "Use_in_System",
        "Notes",
    ),
    EntityType.REQUIREMENT: (
        "Dimension",
        "Requirement_Name",
        "Requirement_Summary",
        "Applicability",
        "Verification_Method",
        "Not_Verified_Condition",
        "Not_Applicable_Condition",
        "Scope_Limit",
    ),
    EntityType.EVIDENCE_TYPE: (
        "Evidence_Name",
        "Source_Document",
        "Evidence_Category",
        "Extraction_Method",
        "Required_Fields",
        "Used_For",
        "Reliability_Notes",
    ),
    EntityType.RULE: (
        "Rule_Name",
        "Rule_Type",
        "Satisfied_Condition",
        "Partially_Satisfied_Condition",
        "Not_Satisfied_Condition",
        "Not_Verified_Condition",
        "Not_Applicable_Condition",
        "Output_Statuses",
        "Officiality",
    ),
}


def stable_chroma_id(kb_version: str, entity_type: EntityType, official_id: str) -> str:
    """Stable across runs while isolating the same source ID by KB version."""
    return f"{kb_version}:{entity_type.value}:{official_id}"


def _render_value(value: object) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value)


def embedding_text(record: NormalizedRecord) -> str | None:
    """Returns reviewed text only for explicitly approved entity/field sets."""
    fields = _EMBEDDED_FIELDS.get(record.entity_type)
    if fields is None:
        return None
    lines = [
        f"Entity Type: {record.entity_type.value}",
        f"Official ID: {record.official_id}",
        f"Provenance: {record.provenance_category.value}",
    ]
    for field in fields:
        value = record.data.get(field)
        if value is None or value == "" or value == []:
            continue
        lines.append(f"{field.replace('_', ' ')}: {_render_value(value)}")
    return "\n".join(lines)


def build_embeddable_records(
    records: Sequence[NormalizedRecord], *, kb_version: str, kb_hash: str
) -> list[EmbeddableRecord]:
    requirements = {
        record.official_id: record
        for record in records
        if record.entity_type is EntityType.REQUIREMENT
    }
    result: list[EmbeddableRecord] = []
    for record in records:
        text = embedding_text(record)
        if text is None:
            continue

        requirement_id: str | None = None
        rule_id: str | None = None
        dimension: str | None = None
        if record.entity_type is EntityType.REQUIREMENT:
            requirement_id = record.official_id
            dimension_value = record.data.get("Dimension")
            dimension = str(dimension_value) if dimension_value else None
        elif record.entity_type is EntityType.RULE:
            requirement_value = record.data.get("Requirement_ID")
            requirement_id = str(requirement_value) if requirement_value else None
            rule_id = record.official_id
            requirement = requirements.get(requirement_id or "")
            if requirement is not None and requirement.data.get("Dimension"):
                dimension = str(requirement.data["Dimension"])

        result.append(
            EmbeddableRecord(
                record_id=stable_chroma_id(kb_version, record.entity_type, record.official_id),
                official_id=record.official_id,
                text=text,
                entity_type=record.entity_type.value,
                dimension=dimension,
                requirement_id=requirement_id,
                rule_id=rule_id,
                provenance_category=record.provenance_category.value,
                kb_version=kb_version,
                kb_hash=kb_hash,
                source_workbook=record.source_workbook,
                source_row_number=record.source_row_number,
                record_hash=record.record_hash,
            )
        )
    return result
