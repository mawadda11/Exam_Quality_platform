from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.domain import LanguageCode, UserType

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) > 320 or not _EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid email address.")
    return normalized


def _validate_password(value: str) -> str:
    if len(value) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    if len(value) > 128:
        raise ValueError("Password must contain at most 128 characters.")
    if not any(character.isalpha() for character in value):
        raise ValueError("Password must include at least one letter.")
    if not any(character.isdigit() for character in value):
        raise ValueError("Password must include at least one number.")
    return value


class FacultyUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    institution: str | None
    department: str | None
    user_type: UserType
    email_verified: bool
    preferred_language: LanguageCode
    created_at: datetime


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = Field(min_length=2, max_length=200)
    institution: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    preferred_language: LanguageCode = LanguageCode.ARABIC

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("Display name must contain at least 2 characters.")
        return stripped

    @field_validator("institution", "department")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class AuthSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: FacultyUserResponse


class PasswordResetRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class PasswordResetRequestResponse(BaseModel):
    message: str
    # Development/test only. It is always null in production.
    debug_reset_token: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password(value)


class UserPreferencesRequest(BaseModel):
    preferred_language: LanguageCode


class MessageResponse(BaseModel):
    message: str
