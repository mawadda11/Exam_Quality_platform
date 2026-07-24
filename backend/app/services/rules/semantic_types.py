from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.domain import AcademicStatus
from app.services.rules.semantic_governance import SemanticRuleSpec


class SemanticAiOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    rule_id: str
    requirement_id: str
    status: AcademicStatus
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: list[uuid.UUID]
    explanation: str = Field(min_length=1, max_length=4000)
    recommendation_id: str | None
    provider: str
    model: str
    prompt_template_version: str
    kb_version: str

    @field_validator("evidence_ids")
    @classmethod
    def evidence_ids_are_unique(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_ids must not contain duplicates.")
        return value

    @field_validator(
        "rule_id",
        "requirement_id",
        "explanation",
        "provider",
        "model",
        "prompt_template_version",
        "kb_version",
    )
    @classmethod
    def strings_are_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be blank.")
        return value.strip()


@dataclass(frozen=True)
class SemanticValidationContext:
    analysis_id: uuid.UUID
    rule_spec: SemanticRuleSpec
    prompt_template_version: str
    kb_version: str
    allowed_evidence_ids: frozenset[uuid.UUID]
    allowed_evidence_types: frozenset[str]


@dataclass(frozen=True)
class ValidatedSemanticResult:
    status: AcademicStatus
    confidence: float
    evidence_ids: list[uuid.UUID]
    explanation: str
    recommendation_id: str | None
    provider: str
    model: str
    prompt_template_version: str
    kb_version: str
