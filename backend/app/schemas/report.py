from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.core.domain import ExamType, ProcessingStage, ReportFormat, ReportLanguage

ReportLibraryStatus = Literal["available", "not_generated", "outdated", "insufficient_evidence"]
ReportLibrarySort = Literal["newest", "oldest", "course", "score"]


class ReportCreateRequest(BaseModel):
    language: ReportLanguage = ReportLanguage.ENGLISH


class ReportResponse(BaseModel):
    """Metadata only - matches docs/API_SPECIFICATION.md's "GET /reports/{id}
    metadata" vs. "GET /reports/{id}/download" split. The PDF bytes are only
    available via the download endpoint."""

    model_config = {"from_attributes": True}

    id: UUID
    analysis_id: UUID
    format: ReportFormat
    language: ReportLanguage
    kb_version: str
    capability_version: str | None
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


class ReportLibraryAnalysisResponse(BaseModel):
    id: UUID
    course_code: str
    course_name: str
    exam_type: ExamType
    term: str
    state: ProcessingStage
    capability_version: str | None
    predecessor_analysis_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ReportLibraryItemResponse(BaseModel):
    status: ReportLibraryStatus
    analysis: ReportLibraryAnalysisResponse
    report: ReportResponse | None


class ReportLibraryPageResponse(BaseModel):
    items: list[ReportLibraryItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
