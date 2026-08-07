from __future__ import annotations

import json
import uuid
from dataclasses import replace

from fastapi.testclient import TestClient
from helpers import auth_header
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import (
    ExtractionWarningSeverity,
    ProcessingStage,
    QuestionReviewStatus,
    QuestionType,
)
from app.models.analysis import Analysis
from app.models.extraction_warning import ExtractionWarning
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.question_source_span import QuestionSourceSpan
from app.schemas.extraction_review import ExtractionReviewSnapshot
from app.services.extraction.persistence import persist_extraction_result
from app.services.extraction.review_snapshot import materialize_initial_review_revision
from app.services.extraction.review_workflow import (
    append_extraction_review_revision,
    confirm_extraction_review,
    get_extraction_review,
)
from app.services.extraction.types import (
    ExtractedQuestion,
    ExtractedQuestionOption,
    ExtractedSourceLine,
    ExtractionReconciliationWarning,
    ExtractionResult,
    Geometry,
)


def _analysis(client: TestClient, email: str) -> uuid.UUID:
    response = client.post(
        "/api/v1/analyses",
        headers=auth_header(email),
        json={
            "course": {"code": "REV-200", "name": "Review v2"},
            "exam_type": "Final",
            "term": "2026",
        },
    )
    assert response.status_code == 201
    return uuid.UUID(response.json()["id"])


def _result(*, warning_code: str = "OPTION_MISSING") -> ExtractionResult:
    stem = ExtractedSourceLine(
        source_line_id="P1-N1",
        provider="pdfplumber",
        provider_version=None,
        page_number=1,
        reading_order=1,
        original_text="Question 1: Choose [1]",
        geometry=Geometry(10, 10, 200, 20),
        confidence=0.98,
        extraction_method="direct_text",
        language="en",
    )
    option_line = ExtractedSourceLine(
        source_line_id="P1-N2",
        provider="pdfplumber",
        provider_version=None,
        page_number=1,
        reading_order=2,
        original_text="A) Alpha",
        geometry=Geometry(10, 25, 120, 35),
        confidence=0.96,
        extraction_method="direct_text",
        language="en",
    )
    option = ExtractedQuestionOption(
        local_key="P1-Q1-O1",
        question_local_key="P1-Q1",
        option_label="A",
        option_text="Alpha",
        sequence=1,
        page_number=1,
        confidence=0.96,
        geometry=option_line.geometry,
        source_line_ids=(option_line.source_line_id,),
    )
    question = ExtractedQuestion(
        number_label="1",
        text=stem.original_text,
        page_number=1,
        parent_number_label=None,
        marks=1,
        sequence=1,
        confidence=0.98,
        geometry=stem.geometry,
        local_key="P1-Q1",
        question_type=QuestionType.MULTIPLE_CHOICE,
        extraction_method="direct_text",
        review_status=QuestionReviewStatus.NEEDS_REVIEW,
        source_line_ids=(stem.source_line_id,),
        options=(option,),
    )
    warning = ExtractionReconciliationWarning(
        code=warning_code,
        severity=ExtractionWarningSeverity.CRITICAL,
        message="One source path omitted an option.",
        page_number=1,
        source_line_ids=(option_line.source_line_id,),
        geometry=option_line.geometry,
    )
    return ExtractionResult(
        questions=[question],
        evidence=[],
        source_lines=[stem, option_line],
        reconciliation_warnings=[warning],
    )


def _hierarchical_result(*, child_marks: tuple[float | None, float | None]) -> ExtractionResult:
    base = _result()
    parent = replace(
        base.questions[0],
        number_label="Q2",
        text="Question 2 - True or False [5]",
        marks=5,
        question_type=QuestionType.TRUE_FALSE,
        options=(),
    )
    children = [
        replace(
            parent,
            number_label=f"Q2({label})",
            text=f"Statement {label}",
            parent_number_label="Q2",
            local_key=f"P1-Q2-{label}",
            parent_local_key="P1-Q1",
            marks=marks,
            sequence=index + 1,
        )
        for index, (label, marks) in enumerate(zip(("a", "b"), child_marks, strict=True))
    ]
    return replace(base, questions=[parent, *children], reconciliation_warnings=[])


def test_v1_snapshots_remain_readable_with_safe_defaults() -> None:
    snapshot = ExtractionReviewSnapshot.model_validate_json(
        json.dumps(
            {
                "schema_version": 1,
                "questions": [],
                "evidence": [],
                "clos": [],
                "topics": [],
                "assessment_records": [],
            }
        )
    )
    assert snapshot.schema_version == 1
    assert snapshot.question_options == []
    assert snapshot.extraction_warnings == []


def test_v2_persists_provenance_keeps_critical_warning_advisory_and_materializes_review(
    client: TestClient,
    db_engine: Engine,
) -> None:
    analysis_id = _analysis(client, "review-v2@example.edu")
    with Session(db_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        persist_extraction_result(session, analysis.id, _result())
        analysis.state = ProcessingStage.REVIEW_READY
        revision = materialize_initial_review_revision(session, analysis.id)
        session.commit()

        snapshot = ExtractionReviewSnapshot.model_validate_json(json.dumps(revision.snapshot))
        assert snapshot.schema_version == 2
        assert snapshot.question_options[0].option_text == "Alpha"
        assert {item.source_line_id for item in snapshot.question_source_spans} == {
            "P1-N1",
            "P1-N2",
        }
        response = get_extraction_review(session, analysis)
        assert response.can_edit is True
        assert response.can_confirm is True
        assert response.confirmation_blockers == []
        assert response.blocking_extraction_warning_ids == []

        candidate = response.snapshot.model_copy(deep=True)
        candidate.questions[0].question_type = QuestionType.SHORT_ANSWER
        candidate.question_options[0].option_text = "Reviewed Alpha"
        candidate.extraction_warnings[0].resolved = True
        saved = append_extraction_review_revision(
            session,
            analysis,
            base_revision_id=response.revision_id,
            candidate_snapshot=candidate,
        )
        assert saved.can_confirm is True
        confirmed = confirm_extraction_review(
            session,
            analysis,
            revision_id=saved.revision_id,
        )
        session.commit()

        question = session.execute(
            select(Question).where(Question.analysis_id == analysis_id)
        ).scalar_one()
        option = session.execute(
            select(QuestionOption).where(QuestionOption.question_id == question.id)
        ).scalar_one()
        warning = session.execute(
            select(ExtractionWarning).where(ExtractionWarning.analysis_id == analysis_id)
        ).scalar_one()
        spans = (
            session.execute(
                select(QuestionSourceSpan).where(QuestionSourceSpan.question_id == question.id)
            )
            .scalars()
            .all()
        )
        assert confirmed.revision_id == saved.revision_id
        assert question.question_type is QuestionType.SHORT_ANSWER
        assert question.review_status is QuestionReviewStatus.REVIEWED
        assert option.option_text == "Reviewed Alpha"
        assert warning.resolved is True
        assert len(spans) == 2


def test_advisory_critical_warning_is_audited_but_does_not_block_confirmation(
    client: TestClient,
    db_engine: Engine,
) -> None:
    analysis_id = _analysis(client, "review-advisory@example.edu")
    with Session(db_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        persist_extraction_result(session, analysis.id, _result(warning_code="MARKS_MISMATCH"))
        analysis.state = ProcessingStage.REVIEW_READY
        materialize_initial_review_revision(session, analysis.id)
        session.commit()

        response = get_extraction_review(session, analysis)
        assert response.snapshot.extraction_warnings[0].resolved is False
        assert response.can_confirm is True
        assert response.confirmation_blockers == []
        assert response.blocking_extraction_warning_ids == []

        confirmed = confirm_extraction_review(
            session,
            analysis,
            revision_id=response.revision_id,
        )
        session.commit()
        assert confirmed.revision_id == response.revision_id


def test_parent_total_with_null_child_marks_is_valid_and_confirmable(
    client: TestClient,
    db_engine: Engine,
) -> None:
    analysis_id = _analysis(client, "review-parent-total@example.edu")
    with Session(db_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        persist_extraction_result(
            session,
            analysis.id,
            _hierarchical_result(child_marks=(None, None)),
        )
        analysis.state = ProcessingStage.REVIEW_READY
        materialize_initial_review_revision(session, analysis.id)
        session.commit()

        response = get_extraction_review(session, analysis)
        assert response.can_confirm is True
        assert response.confirmation_blockers == []


def test_verified_parent_child_marks_mismatch_blocks_until_marks_are_corrected(
    client: TestClient,
    db_engine: Engine,
) -> None:
    analysis_id = _analysis(client, "review-marks-blocker@example.edu")
    with Session(db_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        persist_extraction_result(
            session,
            analysis.id,
            _hierarchical_result(child_marks=(2, 2)),
        )
        analysis.state = ProcessingStage.REVIEW_READY
        materialize_initial_review_revision(session, analysis.id)
        session.commit()

        response = get_extraction_review(session, analysis)
        assert response.can_confirm is False
        assert "saved child marks total 4" in response.confirmation_blockers[0]

        candidate = response.snapshot.model_copy(deep=True)
        child = next(item for item in candidate.questions if item.number_label == "Q2(b)")
        child.marks = 3
        saved = append_extraction_review_revision(
            session,
            analysis,
            base_revision_id=response.revision_id,
            candidate_snapshot=candidate,
        )
        assert saved.can_confirm is True
        assert saved.confirmation_blockers == []
