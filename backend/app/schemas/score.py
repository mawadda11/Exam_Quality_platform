from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from app.core.domain import AcademicStatus
from app.services.rules.scoring import calculate_overall_score, count_statuses, scoreable_statuses

if TYPE_CHECKING:
    from app.models.finding import Finding


class AnalysisScoreResponse(BaseModel):
    """Read-time aggregation over an analysis's current Findings - never
    persisted (see docs/DATABASE_SCHEMA.md's M9 note). Reuses the same
    calculate_overall_score used since M6; this schema only adds the
    per-status counts and denominator explanation SCORE023-SCORE025
    (docs/SCORING_POLICY.md) require the UI to show."""

    model_config = {"from_attributes": True}

    analysis_id: UUID
    score: Decimal | None
    label: str | None
    denominator: int
    satisfied_count: int
    partially_satisfied_count: int
    not_satisfied_count: int
    not_verified_count: int
    not_applicable_count: int
    score_mode: str = "governed"
    excluded_local_semantic_count: int = 0

    @classmethod
    def from_findings(cls, analysis_id: UUID, findings: Sequence[Finding]) -> AnalysisScoreResponse:
        all_statuses = [finding.status for finding in findings]
        scored_statuses, local_only, excluded_count = scoreable_statuses(findings)
        result = calculate_overall_score(scored_statuses)
        counts = count_statuses(scored_statuses if local_only else all_statuses)
        return cls(
            analysis_id=analysis_id,
            score=result.score,
            label=result.label,
            denominator=result.denominator,
            satisfied_count=counts[AcademicStatus.SATISFIED],
            partially_satisfied_count=counts[AcademicStatus.PARTIALLY_SATISFIED],
            not_satisfied_count=counts[AcademicStatus.NOT_SATISFIED],
            not_verified_count=counts[AcademicStatus.NOT_VERIFIED],
            not_applicable_count=counts[AcademicStatus.NOT_APPLICABLE],
            score_mode="local_preliminary" if local_only else "governed",
            excluded_local_semantic_count=excluded_count,
        )
