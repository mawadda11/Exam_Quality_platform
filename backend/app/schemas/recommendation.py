from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from app.core.domain import AcademicStatus

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.services.knowledge_base.reference_data import RecommendationDisplay


class RecommendationResponse(BaseModel):
    """Not persisted - resolved at read time from the Finding it explains
    plus the matching 08_recommendations.xlsx row (see
    app.services.knowledge_base.reference_data.get_recommendations_for).
    One row per (Finding, matching KB recommendation) pair; a Finding with
    no matching KB row (Satisfied/Not Applicable, per SCORE021) simply
    produces none."""

    model_config = {"from_attributes": True}

    finding_id: UUID
    requirement_id: str
    rule_id: str
    status: AcademicStatus
    recommendation_id: str
    title: str
    text: str
    target_user: str
    recommendation_type: str

    @classmethod
    def from_finding(
        cls, finding: Finding, display: RecommendationDisplay
    ) -> RecommendationResponse:
        return cls(
            finding_id=finding.id,
            requirement_id=finding.requirement_id,
            rule_id=finding.rule_id,
            status=finding.status,
            recommendation_id=display.recommendation_id,
            title=display.title,
            text=display.text,
            target_user=display.target_user,
            recommendation_type=display.recommendation_type,
        )
