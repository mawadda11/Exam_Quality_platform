from __future__ import annotations

import copy
import io
import uuid

import pytest
from fastapi.testclient import TestClient
from helpers import auth_header
from pdf_fixtures import build_synthetic_exam_pdf
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from tp153_pdf_fixtures import build_complete_tp153_pdf

from app.core.domain import ProcessingStage
from app.models.analysis import Analysis
from app.models.evidence import Evidence
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.models.processing_event import ProcessingEvent
from app.models.question import Question
from app.models.question_option import QuestionOption
from app.models.topic import Topic

ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}


def _paused_analysis(
    client: TestClient,
    email: str,
    question_preparation_mode: str | None = None,
) -> str:
    created = client.post(
        "/api/v1/analyses",
        json=ANALYSIS_PAYLOAD,
        headers=auth_header(email),
    )
    assert created.status_code == 201
    analysis_id: str = created.json()["id"]
    for file_type, content in (
        ("exam", build_synthetic_exam_pdf()),
        ("tp153", build_complete_tp153_pdf()),
    ):
        uploaded = client.post(
            f"/api/v1/analyses/{analysis_id}/files",
            headers=auth_header(email),
            data={"file_type": file_type},
            files={"file": (f"{file_type}.pdf", io.BytesIO(content), "application/pdf")},
        )
        assert uploaded.status_code == 201
    started = client.post(
        f"/api/v1/analyses/{analysis_id}/run",
        headers=auth_header(email),
        json=(
            {"question_preparation_mode": question_preparation_mode}
            if question_preparation_mode is not None
            else None
        ),
    )
    assert started.status_code == 202
    progress = client.get(
        f"/api/v1/analyses/{analysis_id}/progress",
        headers=auth_header(email),
    )
    assert progress.json()["state"] == "review_ready"
    return analysis_id


def _get_review(client: TestClient, analysis_id: str, email: str) -> dict[str, object]:
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
    )
    assert response.status_code == 200
    return response.json()


def test_review_get_returns_latest_and_original_source_anchored_snapshot(
    client: TestClient,
) -> None:
    email = "review-get@example.test"
    analysis_id = _paused_analysis(client, email)

    body = _get_review(client, analysis_id, email)

    assert body["analysis_id"] == analysis_id
    assert body["revision_number"] == 1
    assert body["snapshot"] == body["original_snapshot"]
    assert body["can_edit"] is True
    assert body["can_confirm"] is True
    assert body["is_confirmed"] is False
    assert body["confirmation_blockers"] == []
    questions = body["snapshot"]["questions"]
    assert questions
    assert questions[0]["page_number"] >= 1
    assert 0 <= questions[0]["extraction_confidence"] <= 1


def test_review_save_creates_immutable_revision_and_rejects_stale_or_new_source_rows(
    client: TestClient,
    db_engine: Engine,
) -> None:
    email = "review-save@example.test"
    analysis_id = _paused_analysis(client, email)
    initial = _get_review(client, analysis_id, email)
    candidate = copy.deepcopy(initial["snapshot"])
    question = candidate["questions"][0]
    question["number_label"] = "Q1 corrected"
    question["question_text"] = "Corrected source-faithful question transcription."
    question["geometry"] = {"x0": 40.0, "top": 80.0, "x1": 500.0, "bottom": 240.0}

    saved = client.put(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
        json={"base_revision_id": initial["revision_id"], "snapshot": candidate},
    )

    assert saved.status_code == 201, saved.text
    saved_body = saved.json()
    assert saved_body["revision_number"] == 2
    assert saved_body["snapshot"]["questions"][0]["question_text"].startswith("Corrected")
    assert saved_body["snapshot"]["questions"][0]["geometry"]["bottom"] == 240.0
    linked_question_evidence = [
        item
        for item in saved_body["snapshot"]["evidence"]
        if item["question_source_record_id"] == question["source_record_id"]
        and item["evidence_type"] == "question_text"
    ]
    assert linked_question_evidence[0]["item_reference"] == "Q1 corrected"
    assert linked_question_evidence[0]["extracted_text"].startswith("Corrected")

    stale = client.put(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
        json={"base_revision_id": initial["revision_id"], "snapshot": candidate},
    )
    assert stale.status_code == 409
    assert "Reload" in stale.json()["detail"]

    fabricated = copy.deepcopy(saved_body["snapshot"])
    fabricated_question = copy.deepcopy(fabricated["questions"][0])
    fabricated_question["source_record_id"] = str(uuid.uuid4())
    fabricated_question["parent_source_record_id"] = None
    fabricated_question["number_label"] = "Q-new"
    fabricated_question["sequence"] = 999
    fabricated["questions"].append(fabricated_question)
    rejected = client.put(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
        json={"base_revision_id": saved_body["revision_id"], "snapshot": fabricated},
    )
    assert rejected.status_code == 422
    assert "manual_review" in rejected.json()["detail"]

    changed_anchor = copy.deepcopy(saved_body["snapshot"])
    changed_anchor["questions"][0]["page_number"] += 1
    rejected_anchor = client.put(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
        json={"base_revision_id": saved_body["revision_id"], "snapshot": changed_anchor},
    )
    assert rejected_anchor.status_code == 422
    assert "immutable source anchor" in rejected_anchor.json()["detail"]

    with Session(db_engine) as session:
        revisions = list(
            session.execute(
                select(ExtractionReviewRevision)
                .where(ExtractionReviewRevision.analysis_id == uuid.UUID(analysis_id))
                .order_by(ExtractionReviewRevision.revision_number)
            ).scalars()
        )
        assert [revision.revision_number for revision in revisions] == [1, 2]
        assert revisions[0].snapshot == initial["original_snapshot"]


def test_reviewer_can_add_one_traceable_question_region_without_a_migration(
    client: TestClient,
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.analyses.run_post_confirmation_pipeline",
        lambda analysis_id, revision_id: None,
    )
    email = "review-add-question@example.test"
    analysis_id = _paused_analysis(client, email)
    initial = _get_review(client, analysis_id, email)
    candidate = copy.deepcopy(initial["snapshot"])
    question_id = str(uuid.uuid4())
    evidence_id = str(uuid.uuid4())
    geometry = {"x0": 40.0, "top": 160.0, "x1": 520.0, "bottom": 280.0}
    candidate["questions"].append(
        {
            "source_record_id": question_id,
            "included": True,
            "parent_source_record_id": None,
            "number_label": "Q-review",
            "question_text": "Visible reviewer-added question transcription.",
            "page_number": 1,
            "marks": 2.0,
            "sequence": max(item["sequence"] for item in candidate["questions"]) + 1,
            "extraction_confidence": 1.0,
            "geometry": geometry,
            "question_type": "short_answer",
            "instructions": None,
            "extraction_method": "manual_review",
            "review_status": "reviewed",
        }
    )
    candidate["evidence"].append(
        {
            "source_record_id": evidence_id,
            "included": True,
            "question_source_record_id": question_id,
            "source_document": "exam",
            "evidence_type": "question_text",
            "page_number": 1,
            "item_reference": "Q-review",
            "extracted_text": "Visible reviewer-added question transcription.",
            "extraction_confidence": 1.0,
            "geometry": geometry,
        }
    )

    saved = client.put(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
        json={"base_revision_id": initial["revision_id"], "snapshot": candidate},
    )
    assert saved.status_code == 201, saved.text

    confirmed = client.post(
        f"/api/v1/analyses/{analysis_id}/extraction-review/confirm",
        headers=auth_header(email),
        json={"revision_id": saved.json()["revision_id"]},
    )
    assert confirmed.status_code == 202, confirmed.text

    with Session(db_engine) as session:
        question = session.get(Question, uuid.UUID(question_id))
        evidence = session.get(Evidence, uuid.UUID(evidence_id))
        assert question is not None
        assert question.analysis_id == uuid.UUID(analysis_id)
        assert question.question_text == "Visible reviewer-added question transcription."
        assert question.extraction_method == "manual_review"
        assert question.geometry == geometry
        assert evidence is not None
        assert evidence.question_id == uuid.UUID(question_id)
        assert evidence.geometry == geometry


def test_confirm_exact_latest_revision_materializes_review_and_starts_continuation(
    client: TestClient,
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduled: list[tuple[uuid.UUID, uuid.UUID]] = []

    def record_continuation(analysis_id: uuid.UUID, revision_id: uuid.UUID) -> None:
        scheduled.append((analysis_id, revision_id))

    monkeypatch.setattr(
        "app.api.analyses.run_post_confirmation_pipeline",
        record_continuation,
    )

    email = "review-confirm@example.test"
    analysis_id = _paused_analysis(client, email)
    initial = _get_review(client, analysis_id, email)
    candidate = copy.deepcopy(initial["snapshot"])
    candidate["questions"][0]["question_text"] = "Reviewed question text."
    candidate["questions"][0]["geometry"] = {
        "x0": 35.0,
        "top": 75.0,
        "x1": 510.0,
        "bottom": 250.0,
    }
    top_level_questions = [
        item for item in candidate["questions"] if item["parent_source_record_id"] is None
    ]
    assert len(top_level_questions) >= 2
    reviewed_parent_id = top_level_questions[0]["source_record_id"]
    reparented_question_id = top_level_questions[1]["source_record_id"]
    top_level_questions[1]["parent_source_record_id"] = reviewed_parent_id
    excluded_topic = candidate["topics"][0]
    excluded_topic_id = excluded_topic["source_record_id"]
    excluded_topic_evidence_id = next(
        item["source_record_id"]
        for item in candidate["evidence"]
        if item["evidence_type"] == "topic"
        and item["page_number"] == excluded_topic["page_number"]
        and item["item_reference"] == (excluded_topic["code"] or excluded_topic["text"][:100])
    )
    candidate["topics"][0]["included"] = False

    saved = client.put(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
        json={"base_revision_id": initial["revision_id"], "snapshot": candidate},
    )
    assert saved.status_code == 201, saved.text
    revision_id = saved.json()["revision_id"]

    stale_confirm = client.post(
        f"/api/v1/analyses/{analysis_id}/extraction-review/confirm",
        headers=auth_header(email),
        json={"revision_id": initial["revision_id"]},
    )
    assert stale_confirm.status_code == 409

    confirmed = client.post(
        f"/api/v1/analyses/{analysis_id}/extraction-review/confirm",
        headers=auth_header(email),
        json={"revision_id": revision_id},
    )
    assert confirmed.status_code == 202
    assert confirmed.json()["state"] == "building_evidence"
    assert scheduled == [(uuid.UUID(analysis_id), uuid.UUID(revision_id))]

    with Session(db_engine) as session:
        analysis = session.get(Analysis, uuid.UUID(analysis_id))
        assert analysis is not None
        assert analysis.confirmed_review_id == uuid.UUID(revision_id)
        assert analysis.state == ProcessingStage.BUILDING_EVIDENCE
        question = (
            session.execute(
                select(Question)
                .where(Question.analysis_id == uuid.UUID(analysis_id))
                .order_by(Question.sequence)
            )
            .scalars()
            .first()
        )
        assert question is not None
        assert question.question_text == "Reviewed question text."
        assert question.geometry == {
            "x0": 35.0,
            "top": 75.0,
            "x1": 510.0,
            "bottom": 250.0,
        }
        reparented_question = session.get(Question, uuid.UUID(reparented_question_id))
        assert reparented_question is not None
        assert reparented_question.parent_question_id == uuid.UUID(reviewed_parent_id)
        assert session.get(Topic, uuid.UUID(excluded_topic_id)) is None
        assert session.get(Evidence, uuid.UUID(excluded_topic_evidence_id)) is None
        confirmation_events = list(
            session.execute(
                select(ProcessingEvent).where(
                    ProcessingEvent.analysis_id == uuid.UUID(analysis_id),
                    ProcessingEvent.stage == ProcessingStage.BUILDING_EVIDENCE,
                )
            ).scalars()
        )
        assert len(confirmation_events) == 1

    read_only = _get_review(client, analysis_id, email)
    assert read_only["is_confirmed"] is True
    assert read_only["can_edit"] is False
    assert read_only["can_confirm"] is False

    write_after_confirm = client.put(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
        json={"base_revision_id": revision_id, "snapshot": saved.json()["snapshot"]},
    )
    assert write_after_confirm.status_code == 409


def test_review_endpoints_use_owner_safe_not_found(client: TestClient) -> None:
    owner = "review-owner@example.test"
    analysis_id = _paused_analysis(client, owner)

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header("other-user@example.test"),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found."


def test_confirm_can_exclude_a_question_subtree_and_its_trace_evidence(
    client: TestClient,
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.analyses.run_post_confirmation_pipeline",
        lambda analysis_id, revision_id: None,
    )
    email = "review-exclude-question@example.test"
    analysis_id = _paused_analysis(client, email)
    initial = _get_review(client, analysis_id, email)
    candidate = copy.deepcopy(initial["snapshot"])

    root_id = candidate["questions"][0]["source_record_id"]
    excluded_ids = {root_id}
    changed = True
    while changed:
        changed = False
        for question in candidate["questions"]:
            if (
                question["parent_source_record_id"] in excluded_ids
                and question["source_record_id"] not in excluded_ids
            ):
                excluded_ids.add(question["source_record_id"])
                changed = True

    for question in candidate["questions"]:
        if question["source_record_id"] in excluded_ids:
            question["included"] = False
    excluded_evidence_ids: set[str] = set()
    for evidence in candidate["evidence"]:
        if evidence["question_source_record_id"] in excluded_ids:
            evidence["included"] = False
            excluded_evidence_ids.add(evidence["source_record_id"])

    saved = client.put(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
        json={"base_revision_id": initial["revision_id"], "snapshot": candidate},
    )
    assert saved.status_code == 201, saved.text

    confirmed = client.post(
        f"/api/v1/analyses/{analysis_id}/extraction-review/confirm",
        headers=auth_header(email),
        json={"revision_id": saved.json()["revision_id"]},
    )
    assert confirmed.status_code == 202, confirmed.text

    with Session(db_engine) as session:
        persisted_question_ids = set(
            session.execute(
                select(Question.id).where(Question.analysis_id == uuid.UUID(analysis_id))
            ).scalars()
        )
        persisted_evidence_ids = set(
            session.execute(
                select(Evidence.id).where(Evidence.analysis_id == uuid.UUID(analysis_id))
            ).scalars()
        )
    assert persisted_question_ids.isdisjoint(uuid.UUID(value) for value in excluded_ids)
    assert persisted_evidence_ids.isdisjoint(uuid.UUID(value) for value in excluded_evidence_ids)


def test_structured_template_questions_and_options_materialize_without_invented_marks_or_geometry(
    client: TestClient,
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.analyses.run_post_confirmation_pipeline",
        lambda analysis_id, revision_id: None,
    )
    email = "structured-template-review@example.test"
    analysis_id = _paused_analysis(client, email, "structured_template")
    initial = _get_review(client, analysis_id, email)
    candidate = copy.deepcopy(initial["snapshot"])
    assert candidate["preparation_mode"] == "structured_template"
    assert candidate["questions"] == []

    question_id = str(uuid.uuid4())
    evidence_id = str(uuid.uuid4())
    option_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    candidate["questions"] = [
        {
            "source_record_id": question_id,
            "included": True,
            "parent_source_record_id": None,
            "number_label": "Q1",
            "question_text": "Which pattern constructs a complex object step by step?",
            "page_number": 1,
            "marks": None,
            "sequence": 1,
            "extraction_confidence": 1.0,
            "geometry": None,
            "question_type": "multiple_choice",
            "instructions": None,
            "extraction_method": "structured_template",
            "review_status": "reviewed",
        }
    ]
    candidate["evidence"].append(
        {
            "source_record_id": evidence_id,
            "included": True,
            "question_source_record_id": question_id,
            "source_document": "exam",
            "evidence_type": "question_text",
            "page_number": 1,
            "item_reference": "Q1",
            "extracted_text": "Which pattern constructs a complex object step by step?",
            "extraction_confidence": 1.0,
            "geometry": None,
        }
    )
    candidate["question_options"] = [
        {
            "source_record_id": option_ids[0],
            "included": True,
            "question_source_record_id": question_id,
            "option_label": "A",
            "option_text": "Singleton",
            "sequence": 1,
            "page_number": 1,
            "extraction_confidence": 1.0,
            "geometry": None,
        },
        {
            "source_record_id": option_ids[1],
            "included": True,
            "question_source_record_id": question_id,
            "option_label": "B",
            "option_text": "Builder",
            "sequence": 2,
            "page_number": 1,
            "extraction_confidence": 1.0,
            "geometry": None,
        },
    ]

    saved = client.put(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
        json={"base_revision_id": initial["revision_id"], "snapshot": candidate},
    )
    assert saved.status_code == 201, saved.text
    assert saved.json()["can_confirm"] is True

    confirmed = client.post(
        f"/api/v1/analyses/{analysis_id}/extraction-review/confirm",
        headers=auth_header(email),
        json={"revision_id": saved.json()["revision_id"]},
    )
    assert confirmed.status_code == 202, confirmed.text

    with Session(db_engine) as session:
        question = session.get(Question, uuid.UUID(question_id))
        options = list(
            session.execute(
                select(QuestionOption)
                .where(QuestionOption.question_id == uuid.UUID(question_id))
                .order_by(QuestionOption.sequence)
            ).scalars()
        )
        assert question is not None
        assert question.marks is None
        assert question.geometry is None
        assert question.extraction_method == "structured_template"
        assert [(option.option_label, option.option_text) for option in options] == [
            ("A", "Singleton"),
            ("B", "Builder"),
        ]
