from __future__ import annotations

import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import ExamType, UploadedFileType
from app.models.analysis import Analysis
from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.course import Course
from app.models.evidence import Evidence
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.models.question import Question
from app.models.topic import Topic
from app.models.user import User
from app.schemas.extraction_review import ExtractionReviewSnapshot
from app.services.extraction.review_snapshot import materialize_initial_review_revision


def _analysis(session: Session) -> Analysis:
    suffix = uuid.uuid4().hex
    user = User(email=f"snapshot-{suffix}@example.test", display_name="Snapshot Test")
    course = Course(code=f"SNP-{suffix[:8]}", name="Snapshot Course")
    session.add_all([user, course])
    session.flush()
    analysis = Analysis(
        user_id=user.id,
        course_id=course.id,
        exam_type=ExamType.MIDTERM,
        term="Test",
    )
    session.add(analysis)
    session.flush()
    return analysis


def test_initial_snapshot_maps_only_genuine_persisted_source_rows(db_engine: Engine) -> None:
    with Session(db_engine) as session:
        analysis = _analysis(session)
        parent = Question(
            analysis_id=analysis.id,
            number_label="Q1",
            question_text="Explain a stack.",
            page_number=1,
            marks=5.0,
            sequence=0,
            confidence=0.95,
            geometry={"x0": 1.0, "top": 2.0, "x1": 3.0, "bottom": 4.0},
        )
        session.add(parent)
        session.flush()
        child = Question(
            analysis_id=analysis.id,
            parent_question_id=parent.id,
            number_label="Q1(a)",
            question_text="Give one operation.",
            page_number=1,
            marks=2.0,
            sequence=1,
            confidence=0.9,
            geometry=None,
        )
        session.add(child)
        session.flush()
        evidence = Evidence(
            analysis_id=analysis.id,
            question_id=child.id,
            source_document=UploadedFileType.EXAM,
            evidence_type="question_text",
            page_number=1,
            item_reference="Q1(a)",
            extracted_text="Give one operation.",
            confidence=0.9,
            geometry=None,
        )
        clo = Clo(
            analysis_id=analysis.id,
            code="CLO1",
            text="Apply computing concepts.",
            program_outcome_reference="PLO1",
            page_number=2,
            confidence=0.88,
            geometry=None,
        )
        topic = Topic(
            analysis_id=analysis.id,
            code="T1",
            text="Stacks",
            expected_hours=3.0,
            page_number=3,
            confidence=0.87,
            geometry=None,
        )
        assessment = AssessmentRecord(
            analysis_id=analysis.id,
            method="Midterm",
            activity="Written exam",
            percentage=30.0,
            page_number=4,
            confidence=0.86,
            geometry=None,
        )
        session.add_all([evidence, clo, topic, assessment])
        session.commit()

        revision = materialize_initial_review_revision(session, analysis.id)
        snapshot = ExtractionReviewSnapshot.model_validate_json(json.dumps(revision.snapshot))

        assert revision.revision_number == 1
        assert [item.source_record_id for item in snapshot.questions] == [parent.id, child.id]
        assert snapshot.questions[1].parent_source_record_id == parent.id
        assert snapshot.evidence[0].source_record_id == evidence.id
        assert snapshot.evidence[0].question_source_record_id == child.id
        assert snapshot.clos[0].source_record_id == clo.id
        assert snapshot.topics[0].source_record_id == topic.id
        assert snapshot.assessment_records[0].source_record_id == assessment.id
        assert all(item.included for item in snapshot.questions)
        assert all(item.included for item in snapshot.evidence)
        assert snapshot.questions[0].geometry is not None
        assert snapshot.questions[0].geometry.x0 == 1.0


def test_initial_snapshot_accepts_empty_extraction_without_placeholders(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis = _analysis(session)
        session.commit()

        revision = materialize_initial_review_revision(session, analysis.id)
        snapshot = ExtractionReviewSnapshot.model_validate_json(json.dumps(revision.snapshot))

        assert snapshot.questions == []
        assert snapshot.evidence == []
        assert snapshot.clos == []
        assert snapshot.topics == []
        assert snapshot.assessment_records == []


def test_initial_snapshot_materialization_is_idempotent(db_engine: Engine) -> None:
    with Session(db_engine) as session:
        analysis = _analysis(session)
        session.commit()

        first = materialize_initial_review_revision(session, analysis.id)
        first_id = first.id
        session.commit()
        second = materialize_initial_review_revision(session, analysis.id)
        count = session.scalar(
            select(func.count())
            .select_from(ExtractionReviewRevision)
            .where(ExtractionReviewRevision.analysis_id == analysis.id)
        )

        assert second.id == first_id
        assert count == 1
