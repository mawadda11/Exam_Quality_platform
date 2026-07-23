"""Fixed KB entity-type vocabulary.

Used by the identifier registry (one ID namespace per entity type) and by
09_relationships.xlsx's From_Entity_Type/To_Entity_Type validation, which
must confirm a relationship's declared type matches the actual type of the
entity its ID resolves to.
"""

from __future__ import annotations

from enum import StrEnum


class EntityType(StrEnum):
    REFERENCE = "Reference"
    STANDARD = "Standard"
    CRITERION = "Criterion"
    REQUIREMENT = "Requirement"
    EVIDENCE_TYPE = "EvidenceType"
    RULE = "Rule"
    RECOMMENDATION = "Recommendation"
    MAPPING = "Mapping"
    RELATIONSHIP = "Relationship"
    POLICY = "Policy"
    METADATA = "Metadata"
