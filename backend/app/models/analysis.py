from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.domain import ExamType, ProcessingStage, UploadedFileType, enum_values
from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.assessment_record import AssessmentRecord
    from app.models.clo import Clo
    from app.models.course import Course
    from app.models.evidence import Evidence
    from app.models.finding import Finding
    from app.models.processing_event import ProcessingEvent
    from app.models.question import Question
    from app.models.report import Report
    from app.models.topic import Topic
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
    # M10: reanalysis for a revised exam. RESTRICT (not CASCADE/SET NULL) so a
    # predecessor can never be deleted out from under a linked reanalysis -
    # "never overwrite previous results" extends to never silently losing the
    # link either. Nullable: most analyses have no predecessor.
    predecessor_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analyses.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )

    owner: Mapped[User] = relationship(back_populates="analyses")
    course: Mapped[Course] = relationship(back_populates="analyses")
    files: Mapped[list[UploadedFile]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    events: Mapped[list[ProcessingEvent]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    questions: Mapped[list[Question]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    evidence: Mapped[list[Evidence]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    clos: Mapped[list[Clo]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    topics: Mapped[list[Topic]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    assessment_records: Mapped[list[AssessmentRecord]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    findings: Mapped[list[Finding]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    reports: Mapped[list[Report]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )
    predecessor: Mapped[Analysis | None] = relationship(
        remote_side="Analysis.id", back_populates="reanalyses"
    )
    # passive_deletes=True: without it, SQLAlchemy's default ORM behavior is
    # to UPDATE ... SET predecessor_analysis_id = NULL on any reanalyses
    # before deleting a predecessor (since the column is nullable) - quietly
    # defeating the ondelete="RESTRICT" constraint by clearing the reference
    # itself instead of leaving the database to reject the delete. This
    # tells SQLAlchemy the database owns that behavior.
    reanalyses: Mapped[list[Analysis]] = relationship(
        back_populates="predecessor", passive_deletes=True
    )

    @property
    def exam_uploaded(self) -> bool:
        return any(f.file_type == UploadedFileType.EXAM for f in self.files)

    @property
    def tp153_uploaded(self) -> bool:
        return any(f.file_type == UploadedFileType.TP153 for f in self.files)

    @property
    def ready_for_analysis(self) -> bool:
        return self.exam_uploaded and self.tp153_uploaded
