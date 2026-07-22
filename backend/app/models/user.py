from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import UserType, enum_values
from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis import Analysis


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200))
    institution: Mapped[str | None] = mapped_column(String(200), default=None)
    department: Mapped[str | None] = mapped_column(String(200), default=None)
    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType, native_enum=False, validate_strings=True, values_callable=enum_values),
        default=UserType.FACULTY_MEMBER,
    )

    analyses: Mapped[list[Analysis]] = relationship(back_populates="owner")
