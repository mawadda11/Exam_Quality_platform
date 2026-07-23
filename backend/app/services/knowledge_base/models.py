from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from app.services.knowledge_base.entity_types import EntityType


class ProvenanceCategory(StrEnum):
    """The six approved provenance categories (RAG_AND_AI_DESIGN.md's KB
    ingestion step 3). Every accepted row maps to exactly one - there is no
    "other"/fallback member by design."""

    OFFICIAL_REFERENCE = "official reference"
    OFFICIAL_CRITERION = "official criterion"
    TEMPLATE_EVIDENCE = "template evidence"
    DERIVED_REQUIREMENT = "derived requirement"
    SYSTEM_RULE = "system rule"
    SYSTEM_POLICY = "system policy"


@dataclass(frozen=True)
class ValidationIssue:
    workbook: str
    sheet: str | None
    row_number: int | None
    field: str | None
    value: object
    reason: str

    def format(self) -> str:
        location = self.workbook
        if self.sheet:
            location += f"[{self.sheet}]"
        if self.row_number is not None:
            location += f" row {self.row_number}"
        if self.field:
            location += f" field '{self.field}'"
        return f"{location}: {self.reason} (value={self.value!r})"


class KnowledgeBaseValidationError(RuntimeError):
    """Raised with every collected ValidationIssue - never just the first
    one - so a single run surfaces the full set of problems at once."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        message = "\n".join(issue.format() for issue in issues)
        super().__init__(message)


@dataclass(frozen=True)
class NormalizedRecord:
    entity_type: EntityType
    official_id: str
    data: Mapping[str, object]
    provenance_category: ProvenanceCategory
    source_workbook: str
    source_sheet: str | None
    source_row_number: int
    source_file_hash: str
    record_hash: str
