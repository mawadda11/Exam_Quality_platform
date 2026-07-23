"""Centralized workbook schema definitions for all 11 approved KB workbooks.

This is the single source of truth for required columns, primary IDs,
closed-value enums, boolean-style columns, and foreign-key-shaped columns -
validator.py and normalizer.py both read from here rather than any column
list being duplicated in tests or other modules.

Allowed-value sets are sourced from 10_metadata.xlsx's own
Allowed_Values_or_Format column wherever it documents one (Criterion,
Requirement dimensions here) - confirmed to match the real workbooks'
observed values exactly. Rule.status reuses app.core.domain.AcademicStatus
directly rather than a second hardcoded copy of the same five values.
Columns with no KB-documented closed set and no structural necessity to
close (e.g. Record_Type, Rule_Type, Relationship_Type) are left as
required free text, per the task's "where the workbook or documentation
defines a closed set" scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.core.domain import AcademicStatus, enum_values
from app.services.knowledge_base.entity_types import EntityType

# --- KB-documented closed sets (from 10_metadata.xlsx) ----------------------

CRITERION_OFFICIALITY_VALUES = frozenset(
    {"Official", "Derived from Official Standard", "Official Template Evidence", "System Defined"}
)
CRITERION_SCOPE_STATUS_VALUES = frozenset(
    {"In Scope", "Partially In Scope", "Context Only", "Evidence Source", "Out of Scope"}
)
REQUIREMENT_APPLICABILITY_VALUES = frozenset(
    {
        "Exam evidence only",
        "Exam and TP-153",
        "TP-153 evidence only",
        "Generated report output",
        "Entire analysis",
    }
)
# Reuses the app's own AcademicStatus values rather than a second hardcoded
# list - this KB-declared set and AcademicStatus must always agree.
RULE_STATUS_VALUES = frozenset(enum_values(AcademicStatus))


class ColumnKind(StrEnum):
    STRING = "string"
    ENUM = "enum"
    LIST_ENUM = "list_enum"
    BOOLEAN = "boolean"
    BOOLEAN_TRISTATE = "boolean_tristate"


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    kind: ColumnKind = ColumnKind.STRING
    required: bool = True
    allowed_values: frozenset[str] | None = None
    list_delimiter: str = "; "


@dataclass(frozen=True)
class ForeignKeySpec:
    column: str
    target_entity_type: EntityType


@dataclass(frozen=True)
class WorkbookSchema:
    filename: str
    entity_type: EntityType
    primary_id_column: str
    columns: tuple[ColumnSpec, ...]
    foreign_keys: tuple[ForeignKeySpec, ...] = field(default_factory=tuple)

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.columns)


def _s(name: str, required: bool = True) -> ColumnSpec:
    return ColumnSpec(name=name, kind=ColumnKind.STRING, required=required)


def _bool(name: str, required: bool = True) -> ColumnSpec:
    return ColumnSpec(
        name=name,
        kind=ColumnKind.BOOLEAN,
        required=required,
        allowed_values=frozenset({"Yes", "No"}),
    )


def _tristate(name: str, required: bool = True) -> ColumnSpec:
    return ColumnSpec(
        name=name,
        kind=ColumnKind.BOOLEAN_TRISTATE,
        required=required,
        allowed_values=frozenset({"Yes", "No", "Conditional"}),
    )


def _enum(name: str, allowed_values: frozenset[str], required: bool = True) -> ColumnSpec:
    return ColumnSpec(
        name=name, kind=ColumnKind.ENUM, required=required, allowed_values=allowed_values
    )


REFERENCES = WorkbookSchema(
    filename="01_references.xlsx",
    entity_type=EntityType.REFERENCE,
    primary_id_column="Reference_ID",
    columns=(
        _s("Reference_ID"),
        _s("Reference_Code"),
        _s("Reference_Name"),
        _s("Organization"),
        _s("Version"),
        _s("Document_Type"),
        _s("Role_in_Knowledge_Base"),
        _bool("Official_Source"),
        _s("Scope_Use"),
        _s("Notes", required=False),
    ),
)

STANDARDS = WorkbookSchema(
    filename="02_standards.xlsx",
    entity_type=EntityType.STANDARD,
    primary_id_column="Standard_ID",
    columns=(
        _s("Standard_ID"),
        _s("Reference_ID"),
        _s("Official_Code"),
        _s("Standard_Name"),
        _s("Record_Type"),
        _s("Scope_Status"),
        _s("Evaluation_Use"),
        _s("Inclusion_Reason"),
        _s("Scope_Limit", required=False),
    ),
    foreign_keys=(ForeignKeySpec("Reference_ID", EntityType.REFERENCE),),
)

CRITERIA = WorkbookSchema(
    filename="03_criteria.xlsx",
    entity_type=EntityType.CRITERION,
    primary_id_column="Criterion_ID",
    columns=(
        _s("Criterion_ID"),
        _s("Standard_ID"),
        _s("Criterion_Code"),
        _s("Criterion_Name"),
        _s("Source_Type"),
        _enum("Officiality", CRITERION_OFFICIALITY_VALUES),
        _enum("Scope_Status", CRITERION_SCOPE_STATUS_VALUES),
        _s("Evidence_Source", required=False),
        _s("Use_in_System"),
        _s("Notes", required=False),
    ),
    foreign_keys=(ForeignKeySpec("Standard_ID", EntityType.STANDARD),),
)

REQUIREMENTS = WorkbookSchema(
    filename="04_requirements.xlsx",
    entity_type=EntityType.REQUIREMENT,
    primary_id_column="Requirement_ID",
    columns=(
        _s("Requirement_ID"),
        _s("Criterion_ID"),
        _s("Dimension"),
        _s("Requirement_Name"),
        _s("Requirement_Summary"),
        _s("Source_Type"),
        _s("Officiality"),
        _enum("Applicability", REQUIREMENT_APPLICABILITY_VALUES),
        _s("Verification_Method"),
        _s("Not_Verified_Condition"),
        _s("Not_Applicable_Condition"),
        _s("Scope_Limit", required=False),
    ),
    foreign_keys=(ForeignKeySpec("Criterion_ID", EntityType.CRITERION),),
)

EVIDENCE_TYPES = WorkbookSchema(
    filename="05_evidence_types.xlsx",
    entity_type=EntityType.EVIDENCE_TYPE,
    primary_id_column="Evidence_Type_ID",
    columns=(
        _s("Evidence_Type_ID"),
        _s("Evidence_Name"),
        _s("Source_Document"),
        _s("Evidence_Category"),
        _s("Extraction_Method"),
        _s("Required_Fields"),
        _s("Used_For"),
        _s("Reliability_Notes", required=False),
    ),
)

EVIDENCE_MAPPING = WorkbookSchema(
    filename="06_evidence_mapping.xlsx",
    entity_type=EntityType.MAPPING,
    primary_id_column="Mapping_ID",
    columns=(
        _s("Mapping_ID"),
        _s("Requirement_ID"),
        _s("Evidence_Type_ID"),
        _s("Evidence_Role"),
        _tristate("Mandatory"),
        _s("Applicability_Condition", required=False),
        _s("Missing_Evidence_Result"),
        _s("Notes", required=False),
    ),
    foreign_keys=(
        ForeignKeySpec("Requirement_ID", EntityType.REQUIREMENT),
        ForeignKeySpec("Evidence_Type_ID", EntityType.EVIDENCE_TYPE),
    ),
)

EVALUATION_RULES = WorkbookSchema(
    filename="07_evaluation_rules.xlsx",
    entity_type=EntityType.RULE,
    primary_id_column="Rule_ID",
    columns=(
        _s("Rule_ID"),
        _s("Requirement_ID"),
        _s("Rule_Name"),
        _s("Rule_Type"),
        _s("Satisfied_Condition"),
        _s("Partially_Satisfied_Condition"),
        _s("Not_Satisfied_Condition"),
        _s("Not_Verified_Condition"),
        _s("Not_Applicable_Condition"),
        ColumnSpec(
            name="Output_Statuses", kind=ColumnKind.LIST_ENUM, allowed_values=RULE_STATUS_VALUES
        ),
        _s("Officiality"),
    ),
    foreign_keys=(ForeignKeySpec("Requirement_ID", EntityType.REQUIREMENT),),
)

RECOMMENDATIONS = WorkbookSchema(
    filename="08_recommendations.xlsx",
    entity_type=EntityType.RECOMMENDATION,
    primary_id_column="Recommendation_ID",
    columns=(
        _s("Recommendation_ID"),
        _s("Rule_ID"),
        _s("Recommendation_Title"),
        _s("Recommendation_Text"),
        _s("Trigger_Status"),
        _s("Target_User"),
        _s("Recommendation_Type"),
        _s("Notes", required=False),
    ),
    foreign_keys=(ForeignKeySpec("Rule_ID", EntityType.RULE),),
)

RELATIONSHIPS = WorkbookSchema(
    filename="09_relationships.xlsx",
    entity_type=EntityType.RELATIONSHIP,
    primary_id_column="Relationship_ID",
    columns=(
        _s("Relationship_ID"),
        _s("From_Entity_Type"),
        _s("From_ID"),
        _s("Relationship_Type"),
        _s("To_Entity_Type"),
        _s("To_ID"),
        _s("Status"),
        _s("Notes", required=False),
    ),
    # From_ID/To_ID are polymorphic (target type is declared per-row via
    # From_Entity_Type/To_Entity_Type) - validated by dedicated logic in
    # validator.py, not the generic single-target ForeignKeySpec mechanism.
)

METADATA = WorkbookSchema(
    filename="10_metadata.xlsx",
    entity_type=EntityType.METADATA,  # not part of the cross-reference registry; see validator.py
    primary_id_column="Metadata_ID",
    columns=(
        _s("Metadata_ID"),
        _s("Entity_Name"),
        _s("Field_Name"),
        _s("Data_Type"),
        _tristate("Required"),
        _s("Allowed_Values_or_Format"),
        _s("Default_Value", required=False),
        _s("Description"),
    ),
)

SCORING_POLICY = WorkbookSchema(
    filename="11_scoring_policy.xlsx",
    entity_type=EntityType.POLICY,
    primary_id_column="Policy_ID",
    columns=(
        _s("Policy_ID"),
        _s("Policy_Category"),
        _s("Policy_Name"),
        _s("Policy_Value"),
        _s("Applies_To"),
        _bool("Mandatory"),
        _s("Description"),
    ),
)

ALL_WORKBOOK_SCHEMAS: tuple[WorkbookSchema, ...] = (
    REFERENCES,
    STANDARDS,
    CRITERIA,
    REQUIREMENTS,
    EVIDENCE_TYPES,
    EVIDENCE_MAPPING,
    EVALUATION_RULES,
    RECOMMENDATIONS,
    RELATIONSHIPS,
    METADATA,
    SCORING_POLICY,
)

SCHEMAS_BY_FILENAME: dict[str, WorkbookSchema] = {s.filename: s for s in ALL_WORKBOOK_SCHEMAS}

# Workbooks whose primary IDs participate in the cross-workbook identifier
# registry (task B's explicit list omits Metadata_ID - 10_metadata.xlsx is
# self-descriptive schema documentation, never referenced by another
# workbook's foreign-key-shaped column).
REGISTRY_WORKBOOKS: tuple[WorkbookSchema, ...] = tuple(
    s for s in ALL_WORKBOOK_SCHEMAS if s.filename != METADATA.filename
)
