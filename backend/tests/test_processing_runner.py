from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import app.services.processing.runner as runner
import app.services.processing.stages as stages
from app.core.domain import ExamType, ProcessingStage
from app.db.base import Base
from app.db.session import create_engine_from_url
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.processing_event import ProcessingEvent
from app.models.user import User


@pytest.fixture()
def runner_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Engine, None, None]:
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'runner_test.db'}")
    Base.metadata.create_all(engine)

    @contextmanager
    def scope() -> Generator[Session, None, None]:
        session = Session(engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(runner, "session_scope", scope)
    yield engine
    engine.dispose()


def _create_analysis(engine: Engine) -> uuid.UUID:
    with Session(engine) as session:
        user = User(email="runner@kau.edu.sa", display_name="Runner Test")
        course = Course(code="RUN-100", name="Runner Test Course")
        session.add_all([user, course])
        session.flush()

        analysis = Analysis(
            user_id=user.id, course_id=course.id, exam_type=ExamType.MIDTERM, term="Test"
        )
        session.add(analysis)
        session.commit()
        return analysis.id


def _events_for(engine: Engine, analysis_id: uuid.UUID) -> list[ProcessingEvent]:
    with Session(engine) as session:
        return list(
            session.execute(
                select(ProcessingEvent)
                .where(ProcessingEvent.analysis_id == analysis_id)
                .order_by(ProcessingEvent.created_at)
            ).scalars()
        )


def test_pipeline_runs_every_stage_to_completed(runner_engine: Engine) -> None:
    analysis_id = _create_analysis(runner_engine)

    runner.run_analysis_pipeline(analysis_id)

    with Session(runner_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        assert analysis.state == ProcessingStage.COMPLETED

    events = _events_for(runner_engine, analysis_id)
    assert [e.stage for e in events] == [
        ProcessingStage.VALIDATING,
        ProcessingStage.EXTRACTING_EXAM,
        ProcessingStage.EXTRACTING_TP153,
        ProcessingStage.BUILDING_EVIDENCE,
        ProcessingStage.RETRIEVING_KNOWLEDGE,
        ProcessingStage.APPLYING_RULES,
        ProcessingStage.GENERATING_REPORT,
        ProcessingStage.COMPLETED,
    ]
    assert all(e.message is None for e in events)


def test_pipeline_transitions_to_failed_with_safe_message_on_exception(
    runner_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(analysis: Analysis, session: Session) -> None:
        raise RuntimeError("sensitive internal detail: /etc/secret-config")

    monkeypatch.setitem(stages.STAGE_HANDLERS, ProcessingStage.EXTRACTING_EXAM, boom)

    analysis_id = _create_analysis(runner_engine)
    runner.run_analysis_pipeline(analysis_id)

    with Session(runner_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        assert analysis.state == ProcessingStage.FAILED

    events = _events_for(runner_engine, analysis_id)
    # Only VALIDATING succeeded before EXTRACTING_EXAM raised; the pipeline
    # stops immediately rather than continuing through the remaining stages.
    assert [e.stage for e in events] == [ProcessingStage.VALIDATING, ProcessingStage.FAILED]
    assert events[-1].message == runner.SAFE_FAILURE_MESSAGE
    assert "sensitive internal detail" not in (events[-1].message or "")
    assert "/etc/secret-config" not in (events[-1].message or "")


def test_pipeline_does_nothing_for_unknown_analysis_id(runner_engine: Engine) -> None:
    # Should not raise - just logs and returns.
    runner.run_analysis_pipeline(uuid.uuid4())
