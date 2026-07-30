from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import LanguageCode, UserType, enum_values
from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.password_reset_token import PasswordResetToken


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    institution: Mapped[str | None] = mapped_column(String(200), default=None)
    department: Mapped[str | None] = mapped_column(String(200), default=None)
    password_hash: Mapped[str | None] = mapped_column(String(512), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    preferred_language: Mapped[LanguageCode] = mapped_column(
        Enum(LanguageCode, native_enum=False, validate_strings=True, values_callable=enum_values),
        default=LanguageCode.ARABIC,
    )
    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType, native_enum=False, validate_strings=True, values_callable=enum_values),
        default=UserType.FACULTY_MEMBER,
    )

    analyses: Mapped[list[Analysis]] = relationship(back_populates="owner")
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
