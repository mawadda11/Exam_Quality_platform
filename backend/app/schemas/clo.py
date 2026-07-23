from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CloResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    analysis_id: UUID
    code: str
    text: str
    program_outcome_reference: str | None
    page_number: int
    confidence: float
    geometry: dict[str, Any] | None
    created_at: datetime
