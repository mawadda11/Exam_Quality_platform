from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.domain import ExamType, ProcessingStage, QuestionPreparationMode
from app.schemas.course import CourseInput, CourseResponse
from app.schemas.uploaded_file import UploadedFileResponse
from app.services.rules.versioning import effective_capability_version

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class AnalysisCreateRequest(BaseModel):
    course: CourseInput
    exam_type: ExamType
    term: str = Field(min_length=1, max_length=50)


class AnalysisRunRequest(BaseModel):
    question_preparation_mode: QuestionPreparationMode = QuestionPreparationMode.ASSISTED_PDF


class AnalysisResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    course: CourseResponse
    exam_type: ExamType
    term: str
    state: ProcessingStage
    owner_user_id: UUID
    # Retained for backward compatibility with historical analyses created
    # while reanalysis was available; no current workflow sets this field on
    # newly created analyses. See docs/KNOWN_LIMITATIONS.md.
    predecessor_analysis_id: UUID | None
    uploaded_files: list[UploadedFileResponse]
    exam_uploaded: bool
    tp153_uploaded: bool
    ready_for_analysis: bool
    capability_version: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, analysis: Analysis) -> AnalysisResponse:
        return cls(
            id=analysis.id,
            course=CourseResponse.model_validate(analysis.course),
            exam_type=analysis.exam_type,
            term=analysis.term,
            state=analysis.state,
            owner_user_id=analysis.user_id,
            predecessor_analysis_id=analysis.predecessor_analysis_id,
            uploaded_files=[UploadedFileResponse.model_validate(f) for f in analysis.files],
            exam_uploaded=analysis.exam_uploaded,
            tp153_uploaded=analysis.tp153_uploaded,
            ready_for_analysis=analysis.ready_for_analysis,
            capability_version=effective_capability_version(analysis),
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )
