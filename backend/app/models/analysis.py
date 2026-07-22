from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import ExamType, ProcessingStage, enum_values
from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.uploaded_file import UploadedFile
    from app.models.user import User


class Analysis(TimestampMixin, Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id"), index=True
    )
    exam_type: Mapped[ExamType] = mapped_column(
        Enum(ExamType, native_enum=False, validate_strings=True, values_callable=enum_values)
    )
    term: Mapped[str] = mapped_column(String(50))
    state: Mapped[ProcessingStage] = mapped_column(
        Enum(
            ProcessingStage, native_enum=False, validate_strings=True, values_callable=enum_values
        ),
        default=ProcessingStage.QUEUED,
    )

    owner: Mapped[User] = relationship(back_populates="analyses")
    course: Mapped[Course] = relationship(back_populates="analyses")
    files: Mapped[list[UploadedFile]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
