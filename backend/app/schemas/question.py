from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class QuestionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    analysis_id: UUID
    parent_question_id: UUID | None
    number_label: str
    question_text: str
    page_number: int
    marks: float | None
    sequence: int
    confidence: float
    geometry: dict[str, Any] | None
    created_at: datetime
