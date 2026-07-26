from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.domain import AcademicStatus
from app.services.rules.capability_manifest import (
    DesignDisposition,
    EvaluationMode,
    SupportStatus,
)


class RuleRuntimeDisposition(StrEnum):
    """Runtime accounting for one governed exam-facing rule.

    These values describe implementation/execution coverage, not an academic
    judgment.  In particular, ``not_run`` must never be presented as
    ``Not Verified`` because it indicates a system coverage gap rather than
    missing academic evidence.
    """

    EVALUATED = "evaluated"
    CONDITIONAL_CAPABILITY_GAP = "conditional_capability_gap"
    UNSUPPORTED = "unsupported"
    NOT_RUN = "not_run"


class RuleCoverageEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    rule_id: str
    requirement_name: str
    rule_name: str
    support_status: SupportStatus
    evaluation_mode: EvaluationMode
    design_disposition: DesignDisposition
    runtime_disposition: RuleRuntimeDisposition
    finding_status: AcademicStatus | None = None
    evaluator_type: str | None = None
    implemented_milestone: str | None = None
    reason: str | None = None
    planned_milestone_or_dependency: str | None = None


class RuleCoverageAuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    scope: Literal["exam_facing_rules"] = "exam_facing_rules"
    total_rules: int = Field(ge=0)
    evaluated_rules: int = Field(ge=0)
    conditional_capability_gap_rules: int = Field(ge=0)
    unsupported_rules: int = Field(ge=0)
    not_run_rules: int = Field(ge=0)
    runtime_integrity_ok: bool
    entries: list[RuleCoverageEntryResponse]
