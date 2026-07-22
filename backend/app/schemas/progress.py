from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.domain import ProcessingStage


class ProgressResponse(BaseModel):
    analysis_id: UUID
    state: ProcessingStage
    message: str | None
    updated_at: datetime
