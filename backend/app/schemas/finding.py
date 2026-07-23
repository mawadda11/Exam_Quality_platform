from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from app.core.domain import AcademicStatus, UploadedFileType

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.services.knowledge_base.reference_data import RequirementDisplay


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
