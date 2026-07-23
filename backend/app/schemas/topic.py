from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class TopicResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    analysis_id: UUID
    code: str | None
    text: str
    expected_hours: float | None
    page_number: int
    confidence: float
    geometry: dict[str, Any] | None
    created_at: datetime
