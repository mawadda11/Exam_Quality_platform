from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from app.core.domain import AcademicStatus, UploadedFileType

if TYPE_CHECKING:
    from app.models.finding import Finding


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

    @classmethod
    def from_model(cls, finding: Finding) -> FindingResponse:
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
        )
