from __future__ import annotations

import uuid

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.domain import (
    AcademicStatus,
    ExamType,
    SemanticConfidenceLevel,
)
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.models.finding import Finding
from app.models.user import User
from app.schemas.extraction_review import ExtractionReviewSnapshot


def _analysis(session: Session) -> Analysis:
    suffix = uuid.uuid4().hex
    user = User(email=f"review-{suffix}@example.test", display_name="Review Test")
    course = Course(code=f"REV-{suffix[:8]}", name="Review Foundation")
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


def _empty_snapshot() -> dict[str, object]:
    return ExtractionReviewSnapshot(
        schema_version=1,
        questions=[],
        evidence=[],
        clos=[],
        topics=[],
        assessment_records=[],
    ).model_dump(mode="json")


def test_revision_is_immutable_and_analysis_can_bind_an_exact_revision(db_engine: Engine) -> None:
    with Session(db_engine) as session:
        analysis = _analysis(session)
        revision = ExtractionReviewRevision(
            analysis_id=analysis.id,
            revision_number=1,
            snapshot=_empty_snapshot(),
        )
        session.add(revision)
        session.commit()

        analysis.confirmed_review_id = revision.id
        session.commit()
        session.refresh(analysis)

        assert analysis.confirmed_review_id == revision.id
        assert analysis.confirmed_review is not None
        assert analysis.confirmed_review.revision_number == 1
        assert "updated_at" not in ExtractionReviewRevision.__table__.columns


def test_revision_number_is_unique_within_an_analysis(db_engine: Engine) -> None:
    with Session(db_engine) as session:
        analysis = _analysis(session)
        session.add_all(
            [
                ExtractionReviewRevision(
                    analysis_id=analysis.id,
                    revision_number=1,
                    snapshot=_empty_snapshot(),
                ),
                ExtractionReviewRevision(
                    analysis_id=analysis.id,
                    revision_number=1,
                    snapshot=_empty_snapshot(),
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_m2_finding_fields_are_nullable_and_use_the_authoritative_enum(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis = _analysis(session)
        legacy = Finding(
            analysis_id=analysis.id,
            requirement_id="REQ018",
            rule_id="RULE018",
            status=AcademicStatus.SATISFIED,
            explanation="Legacy deterministic finding.",
            confidence=1.0,
            evaluator_type="deterministic_rule",
        )
        semantic = Finding(
            analysis_id=analysis.id,
            requirement_id="REQ002",
            rule_id="RULE002",
            status=AcademicStatus.NOT_VERIFIED,
            explanation="Future governed semantic finding.",
            confidence=0.0,
            confidence_level=SemanticConfidenceLevel.LOW,
            evaluation_details={
                "schema_version": 1,
                "decision": "Not Verified",
                "evidence_used": [],
                "reasoning": "The required evidence is insufficient.",
                "recommendation": None,
            },
            evaluator_type="semantic_ai",
        )
        session.add_all([legacy, semantic])
        session.commit()

        assert legacy.confidence_level is None
        assert legacy.evaluation_details is None
        assert semantic.confidence_level is SemanticConfidenceLevel.LOW
        assert semantic.evaluation_details is not None
