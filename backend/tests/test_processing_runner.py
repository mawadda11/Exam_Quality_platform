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
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.models.processing_event import ProcessingEvent
from app.models.user import User
from app.services.extraction.review_snapshot import materialize_initial_review_revision


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


def test_pipeline_runs_extraction_stages_and_pauses_at_review_ready(
    runner_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    # This test exercises generic stage-machine mechanics, not extraction
    # itself (that's test_extraction_pipeline.py / test_tp153_extraction_pipeline.py) -
    # all real stage handlers are stubbed back to no-ops so no uploaded files,
    # extracted evidence, KB runtime, or reports are needed.
    for stage in stages.PRE_REVIEW_STAGES:
        monkeypatch.setitem(
            stages.STAGE_HANDLERS,
            stage,
            lambda analysis, session, settings: None,
        )

    analysis_id = _create_analysis(runner_engine)

    runner.run_analysis_pipeline(analysis_id)

    with Session(runner_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        assert analysis.state == ProcessingStage.REVIEW_READY
        revisions = session.execute(
            select(ExtractionReviewRevision).where(
                ExtractionReviewRevision.analysis_id == analysis_id
            )
        ).scalars()
        assert len(list(revisions)) == 1

    events = _events_for(runner_engine, analysis_id)
    assert [e.stage for e in events] == [
        ProcessingStage.VALIDATING,
        ProcessingStage.EXTRACTING_EXAM,
        ProcessingStage.EXTRACTING_TP153,
        ProcessingStage.REVIEW_READY,
    ]
    assert events[-1].message == runner.REVIEW_READY_MESSAGE


def test_repeated_pipeline_execution_does_not_duplicate_revision_or_event(
    runner_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    for stage in stages.PRE_REVIEW_STAGES:
        monkeypatch.setitem(
            stages.STAGE_HANDLERS,
            stage,
            lambda analysis, session, settings: None,
        )
    analysis_id = _create_analysis(runner_engine)

    runner.run_analysis_pipeline(analysis_id)
    runner.run_analysis_pipeline(analysis_id)

    with Session(runner_engine) as session:
        revisions = list(
            session.execute(
                select(ExtractionReviewRevision).where(
                    ExtractionReviewRevision.analysis_id == analysis_id
                )
            ).scalars()
        )
    events = _events_for(runner_engine, analysis_id)
    assert len(revisions) == 1
    assert [event.stage for event in events].count(ProcessingStage.REVIEW_READY) == 1


def test_pipeline_transitions_to_failed_with_safe_message_on_exception(
    runner_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(analysis: Analysis, session: Session, settings: object) -> None:
        raise RuntimeError("sensitive internal detail: /etc/secret-config")

    monkeypatch.setitem(
        stages.STAGE_HANDLERS,
        ProcessingStage.VALIDATING,
        lambda analysis, session, settings: None,
    )
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
    assert events[-1].message == runner.SAFE_FAILURE_MESSAGES[ProcessingStage.EXTRACTING_EXAM]
    assert "sensitive internal detail" not in (events[-1].message or "")
    assert "/etc/secret-config" not in (events[-1].message or "")


def test_pipeline_does_nothing_for_unknown_analysis_id(runner_engine: Engine) -> None:
    # Should not raise - just logs and returns.
    runner.run_analysis_pipeline(uuid.uuid4())


def _prepare_confirmed_analysis(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    analysis_id = _create_analysis(engine)
    with Session(engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        revision = materialize_initial_review_revision(session, analysis_id)
        analysis.confirmed_review_id = revision.id
        analysis.state = ProcessingStage.BUILDING_EVIDENCE
        session.add(
            ProcessingEvent(
                analysis_id=analysis.id,
                stage=ProcessingStage.BUILDING_EVIDENCE,
                message="Extraction review was confirmed; downstream analysis started.",
            )
        )
        session.commit()
        return analysis_id, revision.id


def test_post_confirmation_pipeline_runs_only_downstream_stages_and_completes(
    runner_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    for stage in stages.POST_CONFIRMATION_STAGES:
        monkeypatch.setitem(
            stages.STAGE_HANDLERS,
            stage,
            lambda analysis, session, settings: None,
        )
    analysis_id, revision_id = _prepare_confirmed_analysis(runner_engine)

    runner.run_post_confirmation_pipeline(analysis_id, revision_id)

    with Session(runner_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        assert analysis.state == ProcessingStage.COMPLETED
        assert analysis.confirmed_review_id == revision_id
    events = _events_for(runner_engine, analysis_id)
    assert [event.stage for event in events] == [
        ProcessingStage.BUILDING_EVIDENCE,
        ProcessingStage.RETRIEVING_KNOWLEDGE,
        ProcessingStage.APPLYING_RULES,
        ProcessingStage.GENERATING_REPORT,
        ProcessingStage.COMPLETED,
    ]
    assert events[-1].message == runner.COMPLETED_MESSAGE


def test_post_confirmation_pipeline_ignores_wrong_revision_or_duplicate_run(
    runner_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = 0

    def count_call(analysis: Analysis, session: Session, settings: object) -> None:
        nonlocal called
        called += 1

    for stage in stages.POST_CONFIRMATION_STAGES:
        monkeypatch.setitem(stages.STAGE_HANDLERS, stage, count_call)
    analysis_id, revision_id = _prepare_confirmed_analysis(runner_engine)

    runner.run_post_confirmation_pipeline(analysis_id, uuid.uuid4())
    assert called == 0

    runner.run_post_confirmation_pipeline(analysis_id, revision_id)
    assert called == len(stages.POST_CONFIRMATION_STAGES)
    runner.run_post_confirmation_pipeline(analysis_id, revision_id)
    assert called == len(stages.POST_CONFIRMATION_STAGES)


def test_post_confirmation_pipeline_fails_safely_and_stops(
    runner_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(
        stages.STAGE_HANDLERS,
        ProcessingStage.BUILDING_EVIDENCE,
        lambda analysis, session, settings: None,
    )

    def boom(analysis: Analysis, session: Session, settings: object) -> None:
        raise RuntimeError("private semantic provider detail")

    monkeypatch.setitem(
        stages.STAGE_HANDLERS,
        ProcessingStage.RETRIEVING_KNOWLEDGE,
        boom,
    )
    analysis_id, revision_id = _prepare_confirmed_analysis(runner_engine)

    runner.run_post_confirmation_pipeline(analysis_id, revision_id)

    with Session(runner_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        assert analysis.state == ProcessingStage.FAILED
    events = _events_for(runner_engine, analysis_id)
    assert [event.stage for event in events] == [
        ProcessingStage.BUILDING_EVIDENCE,
        ProcessingStage.FAILED,
    ]
    assert events[-1].message == runner.SAFE_FAILURE_MESSAGES[ProcessingStage.RETRIEVING_KNOWLEDGE]


def test_timed_out_stage_records_a_retryable_failure_boundary(
    runner_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        stages.STAGE_HANDLERS,
        ProcessingStage.BUILDING_EVIDENCE,
        lambda analysis, session, settings: None,
    )

    def time_out(analysis: Analysis, session: Session, settings: object) -> None:
        raise TimeoutError("private provider request exceeded its deadline")

    monkeypatch.setitem(
        stages.STAGE_HANDLERS,
        ProcessingStage.RETRIEVING_KNOWLEDGE,
        time_out,
    )
    analysis_id, revision_id = _prepare_confirmed_analysis(runner_engine)

    runner.run_post_confirmation_pipeline(analysis_id, revision_id)

    failure = _events_for(runner_engine, analysis_id)[-1]
    assert failure.stage is ProcessingStage.FAILED
    assert failure.failed_stage is ProcessingStage.RETRIEVING_KNOWLEDGE
    assert failure.error_code == "KNOWLEDGE_RETRIEVAL_FAILED"
    assert failure.retryable is True
    assert "private provider" not in (failure.message or "")
