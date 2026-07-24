from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.core.domain import ReportFormat


class ReportResponse(BaseModel):
    """Metadata only - matches docs/API_SPECIFICATION.md's "GET /reports/{id}
    metadata" vs. "GET /reports/{id}/download" split. The PDF bytes are only
    available via the download endpoint."""

    model_config = {"from_attributes": True}

    id: UUID
    analysis_id: UUID
    format: ReportFormat
    kb_version: str
    score: Decimal | None
    score_label: str | None
    denominator: int
    satisfied_count: int
    partially_satisfied_count: int
    not_satisfied_count: int
    not_verified_count: int
    not_applicable_count: int
    size_bytes: int
    created_at: datetime
