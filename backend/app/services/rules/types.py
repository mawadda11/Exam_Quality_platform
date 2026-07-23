from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.core.domain import AcademicStatus


@dataclass(frozen=True)
class RuleFindingResult:
    """The outcome of one deterministic rule execution, ready to persist as
    exactly one Finding. evidence_ids may contain duplicates - persistence
    dedupes before creating finding_evidence links."""

    status: AcademicStatus
    explanation: str
    confidence: float
    evidence_ids: list[uuid.UUID] = field(default_factory=list)
