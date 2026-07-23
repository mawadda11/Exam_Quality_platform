from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import AcademicStatus, ExamType, UploadedFileType
from app.db.base import Base
from app.db.session import create_engine_from_url
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.evidence import Evidence
from app.models.finding import Finding, FindingEvidence
from app.models.user import User
from app.services.rules.identifiers import MARKS_AND_TOTAL, NUMBERING
from app.services.rules.persistence import persist_finding
from app.services.rules.types import RuleFindingResult


def _make_engine(tmp_path: Path) -> Engine:
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'rules_persistence_test.db'}")
    Base.metadata.create_all(engine)
    return engine


def _create_analysis(session: Session) -> Analysis:
    user = User(email="rules-persist@kau.edu.sa", display_name="Rules Persist Test")
    course = Course(code="RULES-100", name="Rules Persistence Test Course")
    session.add_all([user, course])
    session.flush()
    analysis = Analysis(user_id=user.id, course_id=course.id, exam_type=ExamType.FINAL, term="Test")
    session.add(analysis)
    session.flush()
    return analysis


def _make_evidence(session: Session, analysis_id, item_reference: str) -> Evidence:
    ev = Evidence(
        analysis_id=analysis_id,
        source_document=UploadedFileType.EXAM,
        evidence_type="question_text",
        page_number=1,
        item_reference=item_reference,
        extracted_text=f"{item_reference} text",
        confidence=1.0,
    )
    session.add(ev)
    session.flush()
    return ev


def test_persist_finding_creates_one_finding_with_official_ids(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        analysis = _create_analysis(session)
        ev = _make_evidence(session, analysis.id, "Q1")
        result = RuleFindingResult(
            status=AcademicStatus.SATISFIED,
            explanation="All good.",
            confidence=1.0,
            evidence_ids=[ev.id],
        )
        persist_finding(session, analysis.id, MARKS_AND_TOTAL, result)
        session.commit()
        analysis_id = analysis.id

    with Session(engine) as session:
        findings = (
            session.execute(select(Finding).where(Finding.analysis_id == analysis_id))
            .scalars()
            .all()
        )
        assert len(findings) == 1
        finding = findings[0]
        assert finding.requirement_id == "REQ018"
        assert finding.rule_id == "RULE018"
        assert finding.status == AcademicStatus.SATISFIED
        assert finding.explanation == "All good."
        assert finding.confidence == 1.0
        assert finding.evaluator_type == "deterministic_rule"
    engine.dispose()


def test_persist_finding_links_all_evidence_rows(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        analysis = _create_analysis(session)
        ev1 = _make_evidence(session, analysis.id, "Q1")
        ev2 = _make_evidence(session, analysis.id, "Q2")
        result = RuleFindingResult(
            status=AcademicStatus.NOT_SATISFIED,
            explanation="Mismatch.",
            confidence=1.0,
            evidence_ids=[ev1.id, ev2.id],
        )
        finding = persist_finding(session, analysis.id, NUMBERING, result)
        session.commit()
        finding_id = finding.id
        ev1_id, ev2_id = ev1.id, ev2.id

    with Session(engine) as session:
        links = (
            session.execute(select(FindingEvidence).where(FindingEvidence.finding_id == finding_id))
            .scalars()
            .all()
        )
        assert {link.evidence_id for link in links} == {ev1_id, ev2_id}
    engine.dispose()


def test_persist_finding_does_not_create_duplicate_links_for_repeated_evidence_id(
    tmp_path: Path,
) -> None:
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        analysis = _create_analysis(session)
        ev = _make_evidence(session, analysis.id, "Q1")
        # Deliberately repeats the same evidence id twice, as a rule function
        # might if it references the same evidence row from two code paths.
        result = RuleFindingResult(
            status=AcademicStatus.SATISFIED,
            explanation="All good.",
            confidence=1.0,
            evidence_ids=[ev.id, ev.id],
        )
        finding = persist_finding(session, analysis.id, MARKS_AND_TOTAL, result)
        session.commit()
        finding_id = finding.id

    with Session(engine) as session:
        links = (
            session.execute(select(FindingEvidence).where(FindingEvidence.finding_id == finding_id))
            .scalars()
            .all()
        )
        assert len(links) == 1
    engine.dispose()


def test_persist_finding_with_no_evidence_creates_no_links(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        analysis = _create_analysis(session)
        result = RuleFindingResult(
            status=AcademicStatus.NOT_APPLICABLE,
            explanation="No declared total marks were found in the exam.",
            confidence=1.0,
            evidence_ids=[],
        )
        finding = persist_finding(session, analysis.id, MARKS_AND_TOTAL, result)
        session.commit()
        finding_id = finding.id

    with Session(engine) as session:
        links = (
            session.execute(select(FindingEvidence).where(FindingEvidence.finding_id == finding_id))
            .scalars()
            .all()
        )
        assert links == []
    engine.dispose()


def test_deleting_analysis_cascades_to_findings_and_finding_evidence(tmp_path: Path) -> None:
    engine = _make_engine(tmp_path)
    with Session(engine) as session:
        analysis = _create_analysis(session)
        ev = _make_evidence(session, analysis.id, "Q1")
        result = RuleFindingResult(
            status=AcademicStatus.SATISFIED,
            explanation="All good.",
            confidence=1.0,
            evidence_ids=[ev.id],
        )
        persist_finding(session, analysis.id, MARKS_AND_TOTAL, result)
        session.commit()
        analysis_id = analysis.id

        session.delete(session.get(Analysis, analysis_id))
        session.commit()

    with Session(engine) as session:
        assert session.execute(select(Finding)).scalars().all() == []
        assert session.execute(select(FindingEvidence)).scalars().all() == []
    engine.dispose()
