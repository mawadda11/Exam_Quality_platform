from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.domain import AcademicStatus, UploadedFileType

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.services.knowledge_base.reference_data import RequirementDisplay


class FindingEvaluationDetails(BaseModel):
    """Versioned internal contract for future governed semantic findings.

    M2 defines this contract but does not persist or expose it. Future
    rule-specific schemas may extend it, while retaining these required core
    fields and using the same schema version.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    decision: AcademicStatus
    evidence_used: list[UUID]
    reasoning: str = Field(min_length=1, max_length=4000)
    recommendation: str | None

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
    evaluator_type: str
    recommendation_id: str | None
    ai_provider: str | None
    ai_model: str | None
    prompt_template_version: str | None
    kb_version: str | None
    created_at: datetime
    evidence: list[FindingEvidenceRefResponse]
    # M9 additions (additive-only - see docs/API_SPECIFICATION.md): sourced
    # verbatim from 04_requirements.xlsx via the requirement_id this Finding
    # already carries, so the Results UI can render a human-readable name,
    # group by dimension, and honor CLAUDE.md's "do not present derived
    # project rules as official quotations" without hardcoding a second copy
    # of KB text in the frontend.
    requirement_name: str
    dimension: str
    source_type: str
    officiality: str

    @classmethod
    def from_model(
        cls, finding: Finding, requirement_display: RequirementDisplay
    ) -> FindingResponse:
        return cls(
            id=finding.id,
            analysis_id=finding.analysis_id,
            requirement_id=finding.requirement_id,
            rule_id=finding.rule_id,
            status=finding.status,
            explanation=finding.explanation,
            confidence=finding.confidence,
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
