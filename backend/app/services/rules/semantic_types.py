from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.domain import AcademicStatus, SemanticConfidenceLevel
from app.services.rules.semantic_governance import SemanticRuleSpec


class SemanticItemJudgment(BaseModel):
    """One concise, evidence-linked semantic judgment.

    The model may interpret relationships, but every source and target must be
    an already-confirmed evidence row supplied by the backend. It may not
    create source records or cite free-form identifiers.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    source_evidence_id: uuid.UUID
    target_evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    status: AcademicStatus
    reasoning: str = Field(min_length=1, max_length=2000)
    reasoning_ar: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("target_evidence_ids")
    @classmethod
    def target_ids_are_unique(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(value) != len(set(value)):
            raise ValueError("target_evidence_ids must not contain duplicates.")
        return value

    @field_validator("reasoning")
    @classmethod
    def reasoning_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reasoning must not be blank.")
        return value.strip()

    @field_validator("reasoning_ar")
    @classmethod
    def reasoning_ar_is_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("reasoning_ar must not be blank when provided.")
        return value.strip()


class SemanticAiOutput(BaseModel):
    """Untrusted structured provider output.

    Numeric confidence is intentionally absent. M6 requires the backend to
    derive the authoritative High/Medium/Low category from validated evidence
    coverage and item completeness rather than trusting model self-assessment.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    rule_id: str
    requirement_id: str
    status: AcademicStatus
    evidence_ids: list[uuid.UUID]
    explanation: str = Field(min_length=1, max_length=4000)
    explanation_ar: str | None = Field(default=None, min_length=1, max_length=4000)
    recommendation_id: str | None
    items: list[SemanticItemJudgment] = Field(min_length=1)
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

    @field_validator("explanation_ar")
    @classmethod
    def explanation_ar_is_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("explanation_ar must not be blank when provided.")
        return value.strip()


@dataclass(frozen=True)
class SemanticValidationContext:
    analysis_id: uuid.UUID
    rule_spec: SemanticRuleSpec
    prompt_template_version: str
    kb_version: str
    allowed_evidence_ids: frozenset[uuid.UUID]
    allowed_evidence_types: frozenset[str]
    required_source_evidence_ids: frozenset[uuid.UUID]
    allowed_target_evidence_ids: frozenset[uuid.UUID]
    relationship_required: bool = False


@dataclass(frozen=True)
class ValidatedSemanticResult:
    status: AcademicStatus
    confidence_level: SemanticConfidenceLevel
    legacy_confidence: float
    evidence_ids: list[uuid.UUID]
    explanation: str
    explanation_ar: str | None
    recommendation_id: str | None
    provider: str
    model: str
    prompt_template_version: str
    kb_version: str
    items: tuple[SemanticItemJudgment, ...]
    confidence_basis: tuple[str, ...]
