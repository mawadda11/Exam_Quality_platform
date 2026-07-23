from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import ExamType, UploadedFileType
from app.db.base import Base
from app.db.session import create_engine_from_url
from app.models.analysis import Analysis
from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.course import Course
from app.models.evidence import Evidence
from app.models.topic import Topic
from app.models.user import User
from app.services.extraction.tp153_persistence import persist_tp153_extraction_result
from app.services.extraction.types import (
    ExtractedAssessmentRecord,
    ExtractedClo,
    ExtractedTopic,
    Geometry,
    Tp153ExtractionResult,
    Tp153MissingEvidence,
)


def _make_engine(tmp_path: Path) -> Engine:
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'tp153_persistence_test.db'}")
    Base.metadata.create_all(engine)
    return engine


def _create_analysis(session: Session) -> Analysis:
    user = User(email="tp153-persist@kau.edu.sa", display_name="TP153 Persist Test")
    course = Course(code="TP153-100", name="TP153 Persistence Test Course")
    session.add_all([user, course])
    session.flush()
    analysis = Analysis(user_id=user.id, course_id=course.id, exam_type=ExamType.FINAL, term="Test")
    session.add(analysis)
    session.flush()
    return analysis


def _result_with_all_sections() -> Tp153ExtractionResult:
    geometry = Geometry(x0=10.0, top=20.0, x1=50.0, bottom=30.0)
    return Tp153ExtractionResult(
        clos=[
            ExtractedClo(
                code="CLO1",
                text="Explain X.",
                program_outcome_reference="PLO2",
                page_number=1,
                confidence=1.0,
                geometry=geometry,
            )
        ],
        topics=[
            ExtractedTopic(
                code="T1",
                text="Intro",
                expected_hours=3.0,
                page_number=1,
                confidence=1.0,
                geometry=geometry,
            )
        ],
        assessment_records=[
            ExtractedAssessmentRecord(
                method="Midterm Exam",
                activity="Written Exam",
                percentage=20.0,
                page_number=2,
                confidence=1.0,
                geometry=geometry,
            )
        ],
        missing_sections=[],
    )


def test_persists_clos_topics_and_assessment_records(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        analysis = _create_analysis(session)
        persist_tp153_extraction_result(session, analysis.id, _result_with_all_sections())
        session.commit()
        analysis_id = analysis.id

    with Session(engine) as session:
        clos = session.execute(select(Clo).where(Clo.analysis_id == analysis_id)).scalars().all()
        topics = (
            session.execute(select(Topic).where(Topic.analysis_id == analysis_id)).scalars().all()
        )
        records = (
            session.execute(
                select(AssessmentRecord).where(AssessmentRecord.analysis_id == analysis_id)
            )
            .scalars()
            .all()
        )

        assert len(clos) == 1
        assert clos[0].code == "CLO1"
        assert clos[0].program_outcome_reference == "PLO2"
        assert clos[0].geometry == {"x0": 10.0, "top": 20.0, "x1": 50.0, "bottom": 30.0}

        assert len(topics) == 1
        assert topics[0].expected_hours == 3.0

        assert len(records) == 1
        assert records[0].method == "Midterm Exam"
        assert records[0].percentage == 20.0
    engine.dispose()


def test_persists_traceable_evidence_for_each_record(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        analysis = _create_analysis(session)
        persist_tp153_extraction_result(session, analysis.id, _result_with_all_sections())
        session.commit()
        analysis_id = analysis.id

    with Session(engine) as session:
        evidence_rows = (
            session.execute(select(Evidence).where(Evidence.analysis_id == analysis_id))
            .scalars()
            .all()
        )
        assert len(evidence_rows) == 3
        assert all(e.source_document == UploadedFileType.TP153 for e in evidence_rows)

        by_type = {e.evidence_type: e for e in evidence_rows}
        assert by_type["clo"].item_reference == "CLO1"
        assert by_type["clo"].page_number == 1
        assert by_type["topic"].item_reference == "T1"
        assert by_type["assessment_record"].item_reference == "Midterm Exam"
        assert by_type["assessment_record"].page_number == 2
    engine.dispose()


def test_missing_section_persists_evidence_marker_and_no_domain_rows(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    result = Tp153ExtractionResult(
        clos=[],
        topics=[],
        assessment_records=[],
        missing_sections=[
            Tp153MissingEvidence(
                section="clos", page_number=2, note="No Course Learning Outcomes section found."
            )
        ],
    )
    with Session(engine) as session:
        analysis = _create_analysis(session)
        persist_tp153_extraction_result(session, analysis.id, result)
        session.commit()
        analysis_id = analysis.id

    with Session(engine) as session:
        clos = session.execute(select(Clo).where(Clo.analysis_id == analysis_id)).scalars().all()
        assert clos == []  # never a fabricated CLO row

        evidence_rows = (
            session.execute(select(Evidence).where(Evidence.analysis_id == analysis_id))
            .scalars()
            .all()
        )
        assert len(evidence_rows) == 1
        marker = evidence_rows[0]
        assert marker.evidence_type == "missing_section"
        assert marker.source_document == UploadedFileType.TP153
        assert marker.item_reference == "clos"
        assert marker.page_number == 2
        assert "Learning Outcomes" in marker.extracted_text
    engine.dispose()
