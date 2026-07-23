from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import ExamType, UploadedFileType
from app.db.base import Base
from app.db.session import create_engine_from_url
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.user import User
from app.services.extraction.persistence import persist_extraction_result
from app.services.extraction.types import (
    ExtractedEvidence,
    ExtractedQuestion,
    ExtractionResult,
    Geometry,
)


def _make_engine(tmp_path: Path) -> Engine:
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'persistence_test.db'}")
    Base.metadata.create_all(engine)
    return engine


def _create_analysis(session: Session) -> Analysis:
    user = User(email="persist@kau.edu.sa", display_name="Persist Test")
    course = Course(code="PER-100", name="Persistence Test Course")
    session.add_all([user, course])
    session.flush()
    analysis = Analysis(
        user_id=user.id, course_id=course.id, exam_type=ExamType.MIDTERM, term="Test"
    )
    session.add(analysis)
    session.flush()
    return analysis


def _sample_result() -> ExtractionResult:
    geometry = Geometry(x0=10.0, top=20.0, x1=50.0, bottom=30.0)
    questions = [
        ExtractedQuestion(
            number_label="Q1",
            text="Q1. Stem.",
            page_number=1,
            parent_number_label=None,
            marks=None,
            sequence=1,
            confidence=1.0,
            geometry=geometry,
        ),
        ExtractedQuestion(
            number_label="Q1(a)",
            text="(a) Part.",
            page_number=1,
            parent_number_label="Q1",
            marks=3.0,
            sequence=2,
            confidence=1.0,
            geometry=geometry,
        ),
    ]
    evidence = [
        ExtractedEvidence(
            evidence_type="question_text",
            page_number=1,
            item_reference="Q1",
            extracted_text="Q1. Stem.",
            confidence=1.0,
            geometry=geometry,
            question_number_label="Q1",
        ),
        ExtractedEvidence(
            evidence_type="marks",
            page_number=1,
            item_reference="Q1(a)",
            extracted_text="[3 marks]",
            confidence=1.0,
            geometry=None,
            question_number_label="Q1(a)",
        ),
        ExtractedEvidence(
            evidence_type="instructions",
            page_number=1,
            item_reference="instructions",
            extracted_text="Instructions: do the thing.",
            confidence=1.0,
            geometry=None,
            question_number_label=None,
        ),
    ]
    return ExtractionResult(questions=questions, evidence=evidence)


def test_persists_questions_with_resolved_parent_link(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        analysis = _create_analysis(session)
        persist_extraction_result(session, analysis.id, _sample_result())
        session.commit()
        analysis_id = analysis.id

    with Session(engine) as session:
        rows = (
            session.execute(
                select(Question)
                .where(Question.analysis_id == analysis_id)
                .order_by(Question.sequence)
            )
            .scalars()
            .all()
        )
        assert len(rows) == 2
        q1, q1a = rows
        assert q1.number_label == "Q1"
        assert q1.parent_question_id is None
        assert q1a.number_label == "Q1(a)"
        assert q1a.parent_question_id == q1.id
        assert q1a.marks == 3.0
        assert q1.geometry == {"x0": 10.0, "top": 20.0, "x1": 50.0, "bottom": 30.0}
    engine.dispose()


def test_persists_evidence_linked_to_question_and_analysis(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        analysis = _create_analysis(session)
        persist_extraction_result(session, analysis.id, _sample_result())
        session.commit()
        analysis_id = analysis.id

    with Session(engine) as session:
        evidence_rows = (
            session.execute(select(Evidence).where(Evidence.analysis_id == analysis_id))
            .scalars()
            .all()
        )
        assert len(evidence_rows) == 3

        by_type = {e.evidence_type: e for e in evidence_rows}
        assert by_type["question_text"].source_document == UploadedFileType.EXAM
        assert by_type["question_text"].item_reference == "Q1"
        assert by_type["question_text"].page_number == 1
        assert by_type["question_text"].question_id is not None

        assert by_type["marks"].question_id is not None
        assert by_type["instructions"].question_id is None
        assert by_type["instructions"].item_reference == "instructions"
    engine.dispose()


def test_evidence_with_unresolvable_question_label_links_to_no_question(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    result = ExtractionResult(
        questions=[],
        evidence=[
            ExtractedEvidence(
                evidence_type="question_text",
                page_number=1,
                item_reference="Q99",
                extracted_text="orphaned",
                confidence=0.6,
                geometry=None,
                question_number_label="Q99",
            )
        ],
    )
    with Session(engine) as session:
        analysis = _create_analysis(session)
        persist_extraction_result(session, analysis.id, result)
        session.commit()
        analysis_id = analysis.id

    with Session(engine) as session:
        rows = (
            session.execute(select(Evidence).where(Evidence.analysis_id == analysis_id))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].question_id is None
    engine.dispose()
