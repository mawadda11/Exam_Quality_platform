from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CourseInput(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=300)
    department: str | None = None
    program: str | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class CourseResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    code: str
    name: str
    department: str | None
    program: str | None
