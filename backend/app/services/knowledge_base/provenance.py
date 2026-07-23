"""Centralized, explicit mapping from each workbook's raw officiality-style
column value to exactly one of the six approved provenance categories.

Traced empirically against the real KB (not guessed): 02_standards.xlsx and
03_criteria.xlsx's provenance-relevant values were cross-checked against
their Reference_ID/Standard_ID lineage to confirm which raw values are
official-accreditation-sourced vs. TP-153-template-sourced vs. derived vs.
system-authored. Workbooks with no per-row officiality signal (05, 06, 08,
09, 10, 11) are inherently system-authored specification/policy content and
map uniformly to "system policy".

classify_provenance returns None - never a guessed default - when a row's
raw value isn't in this table; the caller (validator.py) turns that into a
hard validation failure.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.services.knowledge_base.models import ProvenanceCategory


@dataclass(frozen=True)
class _ConditionalProvenance:
    column: str
    mapping: Mapping[str, ProvenanceCategory]


_PROVENANCE_RULES: dict[str, ProvenanceCategory | _ConditionalProvenance] = {
    "01_references.xlsx": _ConditionalProvenance(
        column="Official_Source",
        mapping={"Yes": ProvenanceCategory.OFFICIAL_REFERENCE},
    ),
    "02_standards.xlsx": _ConditionalProvenance(
        column="Record_Type",
        mapping={
            "Official Standard": ProvenanceCategory.OFFICIAL_CRITERION,
            "Official Substandard": ProvenanceCategory.OFFICIAL_CRITERION,
            "Official Criterion": ProvenanceCategory.OFFICIAL_CRITERION,
            "Official Template Section": ProvenanceCategory.TEMPLATE_EVIDENCE,
        },
    ),
    "03_criteria.xlsx": _ConditionalProvenance(
        column="Officiality",
        mapping={
            "Official": ProvenanceCategory.OFFICIAL_CRITERION,
            "Official Template Evidence": ProvenanceCategory.TEMPLATE_EVIDENCE,
            "Derived from Official Standard": ProvenanceCategory.DERIVED_REQUIREMENT,
            "System Defined": ProvenanceCategory.SYSTEM_POLICY,
        },
    ),
    "04_requirements.xlsx": _ConditionalProvenance(
        column="Officiality",
        mapping={
            "Derived": ProvenanceCategory.DERIVED_REQUIREMENT,
            "System Defined": ProvenanceCategory.SYSTEM_POLICY,
        },
    ),
    "05_evidence_types.xlsx": ProvenanceCategory.SYSTEM_POLICY,
    "06_evidence_mapping.xlsx": ProvenanceCategory.SYSTEM_POLICY,
    "07_evaluation_rules.xlsx": _ConditionalProvenance(
        column="Officiality",
        mapping={"System Rule": ProvenanceCategory.SYSTEM_RULE},
    ),
    "08_recommendations.xlsx": ProvenanceCategory.SYSTEM_POLICY,
    "09_relationships.xlsx": ProvenanceCategory.SYSTEM_POLICY,
    "10_metadata.xlsx": ProvenanceCategory.SYSTEM_POLICY,
    "11_scoring_policy.xlsx": ProvenanceCategory.SYSTEM_POLICY,
}


def classify_provenance(workbook: str, row: Mapping[str, object]) -> ProvenanceCategory | None:
    rule = _PROVENANCE_RULES.get(workbook)
    if rule is None:
        return None
    if isinstance(rule, ProvenanceCategory):
        return rule

    raw_value = row.get(rule.column)
    if raw_value is None:
        return None
    return rule.mapping.get(str(raw_value).strip())
