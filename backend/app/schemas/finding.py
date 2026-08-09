from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.domain import AcademicStatus, SemanticConfidenceLevel, UploadedFileType

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.services.knowledge_base.reference_data import RequirementDisplay


class FindingItemJudgmentDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    source_evidence_id: UUID
    target_evidence_ids: list[UUID] = Field(default_factory=list)
    status: AcademicStatus
    reasoning: str = Field(min_length=1, max_length=2000)
    reasoning_ar: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("target_evidence_ids")
    @classmethod
    def target_ids_are_unique(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("target_evidence_ids must not contain duplicates.")
        return value


class FindingEvaluationDetails(BaseModel):
    """Versioned governed details persisted for semantic findings."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    decision: AcademicStatus
    evidence_used: list[UUID]
    reasoning: str = Field(min_length=1, max_length=4000)
    reasoning_ar: str | None = Field(default=None, min_length=1, max_length=4000)
    recommendation: str | None
    confidence_basis: list[str] = Field(default_factory=list)
    item_judgments: list[FindingItemJudgmentDetails] = Field(default_factory=list)
    retrieved_knowledge_ids: list[str] = Field(default_factory=list)

    @field_validator("evidence_used")
    @classmethod
    def evidence_ids_are_unique(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_used must not contain duplicate evidence IDs.")
        return value

    @field_validator("reasoning")
    @classmethod
    def reasoning_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reasoning must not be blank.")
        return value.strip()

    @field_validator("recommendation")
    @classmethod
    def recommendation_is_controlled_or_absent(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("recommendation must be a controlled recommendation ID or null.")
        return value.strip()

    @field_validator("confidence_basis", "retrieved_knowledge_ids")
    @classmethod
    def list_strings_are_not_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("List values must not be blank.")
        return [item.strip() for item in value]


class FindingEvidenceRefResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    source_document: UploadedFileType
    evidence_type: str
    page_number: int
    item_reference: str


class FindingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    analysis_id: UUID
    requirement_id: str
    rule_id: str
    status: AcademicStatus
    explanation: str
    confidence: float
    confidence_level: SemanticConfidenceLevel | None
    evaluation_details: FindingEvaluationDetails | None
    evaluator_type: str
    recommendation_id: str | None
    ai_provider: str | None
    ai_model: str | None
    prompt_template_version: str | None
    kb_version: str | None
    created_at: datetime
    evidence: list[FindingEvidenceRefResponse]
    requirement_name: str
    dimension: str
    source_type: str
    officiality: str

    @classmethod
    def from_model(
        cls, finding: Finding, requirement_display: RequirementDisplay
    ) -> FindingResponse:
        details = (
            FindingEvaluationDetails.model_validate(finding.evaluation_details, strict=False)
            if finding.evaluation_details is not None
            else None
        )
        return cls(
            id=finding.id,
            analysis_id=finding.analysis_id,
            requirement_id=finding.requirement_id,
            rule_id=finding.rule_id,
            status=finding.status,
            explanation=finding.explanation,
            confidence=finding.confidence,
            confidence_level=finding.confidence_level,
            evaluation_details=details,
            evaluator_type=finding.evaluator_type,
            recommendation_id=finding.recommendation_id,
            ai_provider=finding.ai_provider,
            ai_model=finding.ai_model,
            prompt_template_version=finding.prompt_template_version,
            kb_version=finding.kb_version,
            created_at=finding.created_at,
            evidence=[
                FindingEvidenceRefResponse.model_validate(link.evidence)
                for link in finding.evidence_links
            ],
            requirement_name=requirement_display.requirement_name,
            dimension=requirement_display.dimension,
            source_type=requirement_display.source_type,
            officiality=requirement_display.officiality,
        )
