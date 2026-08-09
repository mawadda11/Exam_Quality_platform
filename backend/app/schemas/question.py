from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.core.domain import QuestionReviewStatus, QuestionType


class QuestionSourceSpanResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    option_id: UUID | None
    provider: str
    provider_version: str | None
    source_line_id: str
    original_text: str
    page_number: int
    geometry: dict[str, Any] | None
    confidence: float | None
    extraction_method: str


class QuestionOptionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    option_label: str
    option_text: str
    sequence: int
    page_number: int
    confidence: float
    geometry: dict[str, Any] | None
    source_spans: list[QuestionSourceSpanResponse]


class QuestionBlankResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    blank_index: int
    source_text: str | None
    page_number: int
    geometry: dict[str, Any] | None


class QuestionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    analysis_id: UUID
    parent_question_id: UUID | None
    number_label: str
    question_text: str
    question_type: QuestionType
    instructions: str | None
    page_number: int
    marks: float | None
    sequence: int
    confidence: float
    geometry: dict[str, Any] | None
    extraction_method: str
    review_status: QuestionReviewStatus
    options: list[QuestionOptionResponse]
    blanks: list[QuestionBlankResponse]
    source_spans: list[QuestionSourceSpanResponse]
    created_at: datetime
