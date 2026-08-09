from __future__ import annotations

import io
import time

import pytest
from fastapi.testclient import TestClient
from helpers import auth_header
from pdf_fixtures import build_synthetic_exam_pdf
from tp153_pdf_fixtures import build_complete_tp153_pdf

import app.services.processing.stages as stages
from app.core.domain import ProcessingStage
from app.models.analysis import Analysis
from app.services.processing.runner import SAFE_FAILURE_MESSAGES

ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}


def _create_analysis(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/analyses", json=ANALYSIS_PAYLOAD, headers=auth_header(email))
    assert response.status_code == 201
    analysis_id: str = response.json()["id"]
    return analysis_id


def _upload(
    client: TestClient, analysis_id: str, email: str, file_type: str, filename: str, content: bytes
) -> None:
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/files",
        headers=auth_header(email),
        data={"file_type": file_type},
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 201


def _make_ready_analysis(client: TestClient, email: str) -> str:
    # Real, parseable exam and TP-153 PDFs are required here (not the
    # minimal fake-PDF fixture) since M4/M5 wired real extraction into both
    # EXTRACTING_EXAM and EXTRACTING_TP153 - these tests care about
    # run/progress mechanics succeeding end-to-end, not extraction
    # correctness itself (see test_extraction_pipeline.py and
    # test_tp153_extraction_pipeline.py for that).
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", build_synthetic_exam_pdf())
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", build_complete_tp153_pdf())
    return analysis_id


def _poll_until_terminal(client: TestClient, analysis_id: str, headers: dict[str, str]) -> dict:
    result: dict = {}
    for _ in range(20):
        response = client.get(f"/api/v1/analyses/{analysis_id}/progress", headers=headers)
        assert response.status_code == 200
        result = response.json()
        if result["state"] in ("review_ready", "completed", "failed"):
            break
        time.sleep(0.05)
    return result


def test_run_rejects_when_files_are_missing(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u1@kau.edu.sa")
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/run", headers=auth_header("u1@kau.edu.sa")
    )
    assert response.status_code == 409


def test_run_rejects_on_analysis_not_owned(client: TestClient) -> None:
    analysis_id = _make_ready_analysis(client, "owner@kau.edu.sa")
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/run", headers=auth_header("intruder@kau.edu.sa")
    )
    assert response.status_code == 404


def test_run_missing_auth_header_returns_401(client: TestClient) -> None:
    analysis_id = _make_ready_analysis(client, "u_auth@kau.edu.sa")
    response = client.post(f"/api/v1/analyses/{analysis_id}/run")
    assert response.status_code == 401


def test_run_starts_pipeline_and_reaches_review_ready(client: TestClient) -> None:
    analysis_id = _make_ready_analysis(client, "u2@kau.edu.sa")
    headers = auth_header("u2@kau.edu.sa")

    run_response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert run_response.status_code == 202

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "review_ready"
    assert progress["message"] == "Extraction is ready for review."


def test_openapi_exposes_review_ready_as_an_additive_processing_stage(
    client: TestClient,
) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    processing_stages = response.json()["components"]["schemas"]["ProcessingStage"]["enum"]
    assert "review_ready" in processing_stages


def test_run_twice_returns_conflict(client: TestClient) -> None:
    analysis_id = _make_ready_analysis(client, "u3@kau.edu.sa")
    headers = auth_header("u3@kau.edu.sa")

    first = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert first.status_code == 202

    second = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert second.status_code == 409


def test_progress_not_owned_returns_404(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "owner2@kau.edu.sa")
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/progress", headers=auth_header("intruder2@kau.edu.sa")
    )
    assert response.status_code == 404


def test_progress_before_run_shows_queued_with_no_message(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u4@kau.edu.sa")
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/progress", headers=auth_header("u4@kau.edu.sa")
    )
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "queued"
    assert body["message"] is None


def test_progress_reports_failed_with_safe_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(analysis: Analysis, session: object, settings: object) -> None:
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setitem(stages.STAGE_HANDLERS, ProcessingStage.EXTRACTING_EXAM, boom)

    analysis_id = _make_ready_analysis(client, "u5@kau.edu.sa")
    headers = auth_header("u5@kau.edu.sa")
    client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "failed"
    assert progress["message"] == SAFE_FAILURE_MESSAGES[ProcessingStage.EXTRACTING_EXAM]
    assert "sensitive internal detail" not in (progress["message"] or "")


def test_failed_pre_review_analysis_can_retry_without_reupload(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = stages.STAGE_HANDLERS[ProcessingStage.EXTRACTING_EXAM]
    calls = 0

    def fail_once(analysis: Analysis, session: object, settings: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("private one-time extraction failure")
        original(analysis, session, settings)

    monkeypatch.setitem(stages.STAGE_HANDLERS, ProcessingStage.EXTRACTING_EXAM, fail_once)

    email = "retry-pre-review@kau.edu.sa"
    analysis_id = _make_ready_analysis(client, email)
    headers = auth_header(email)
    assert client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers).status_code == 202

    failed = _poll_until_terminal(client, analysis_id, headers)
    assert failed["state"] == "failed"
    assert failed["failed_stage"] == "extracting_exam"
    assert failed["error_code"] == "EXAM_EXTRACTION_FAILED"
    assert failed["can_retry"] is True
    assert "private one-time extraction failure" not in failed["message"]

    retried = client.post(f"/api/v1/analyses/{analysis_id}/retry", headers=headers)
    assert retried.status_code == 202
    completed_retry = _poll_until_terminal(client, analysis_id, headers)
    assert completed_retry["state"] == "review_ready"
    assert calls == 2

    duplicate = client.post(f"/api/v1/analyses/{analysis_id}/retry", headers=headers)
    assert duplicate.status_code == 409


def test_retry_is_owner_scoped(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(analysis: Analysis, session: object, settings: object) -> None:
        raise RuntimeError("private failure")

    monkeypatch.setitem(stages.STAGE_HANDLERS, ProcessingStage.EXTRACTING_EXAM, boom)
    analysis_id = _make_ready_analysis(client, "retry-owner@kau.edu.sa")
    owner_headers = auth_header("retry-owner@kau.edu.sa")
    client.post(f"/api/v1/analyses/{analysis_id}/run", headers=owner_headers)
    assert _poll_until_terminal(client, analysis_id, owner_headers)["state"] == "failed"

    response = client.post(
        f"/api/v1/analyses/{analysis_id}/retry",
        headers=auth_header("retry-intruder@kau.edu.sa"),
    )
    assert response.status_code == 404


def test_failed_post_confirmation_analysis_reuses_confirmed_revision_on_retry(
    client: TestClient,
    test_settings: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Use the governed local baseline so the downstream pipeline can finish
    # after the injected one-time knowledge-retrieval failure.
    test_settings.ai_provider = "local"
    test_settings.ai_model = "local-governed-baseline-v1"

    email = "retry-post-confirmation@kau.edu.sa"
    analysis_id = _make_ready_analysis(client, email)
    headers = auth_header(email)
    assert client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers).status_code == 202
    assert _poll_until_terminal(client, analysis_id, headers)["state"] == "review_ready"

    review = client.get(f"/api/v1/analyses/{analysis_id}/extraction-review", headers=headers).json()
    original = stages.STAGE_HANDLERS[ProcessingStage.RETRIEVING_KNOWLEDGE]
    calls = 0

    def fail_once(analysis: Analysis, session: object, settings: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("private one-time retrieval failure")
        original(analysis, session, settings)

    monkeypatch.setitem(
        stages.STAGE_HANDLERS,
        ProcessingStage.RETRIEVING_KNOWLEDGE,
        fail_once,
    )
    confirmed = client.post(
        f"/api/v1/analyses/{analysis_id}/extraction-review/confirm",
        headers=headers,
        json={"revision_id": review["revision_id"]},
    )
    assert confirmed.status_code == 202

    failed = _poll_until_terminal(client, analysis_id, headers)
    assert failed["state"] == "failed"
    assert failed["failed_stage"] == "retrieving_knowledge"
    assert failed["error_code"] == "KNOWLEDGE_RETRIEVAL_FAILED"
    assert failed["can_retry"] is True

    retry = client.post(f"/api/v1/analyses/{analysis_id}/retry", headers=headers)
    assert retry.status_code == 202
    completed = _poll_until_terminal(client, analysis_id, headers)
    assert completed["state"] == "completed"
    assert calls == 2


@pytest.mark.parametrize(
    ("mode", "expects_questions"),
    [
        ("assisted_pdf", True),
        ("manual_pdf", False),
        ("structured_template", False),
    ],
)
def test_run_persists_selected_question_preparation_mode(
    client: TestClient,
    mode: str,
    expects_questions: bool,
) -> None:
    email = f"preparation-{mode}@kau.edu.sa"
    analysis_id = _make_ready_analysis(client, email)
    headers = auth_header(email)

    response = client.post(
        f"/api/v1/analyses/{analysis_id}/run",
        headers=headers,
        json={"question_preparation_mode": mode},
    )

    assert response.status_code == 202, response.text
    assert _poll_until_terminal(client, analysis_id, headers)["state"] == "review_ready"
    review = client.get(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=headers,
    )
    assert review.status_code == 200, review.text
    body = review.json()
    snapshot = body["snapshot"]
    assert snapshot["preparation_mode"] == mode
    assert bool(snapshot["questions"]) is expects_questions
    if mode == "manual_pdf":
        assert body["can_confirm"] is False
        assert "Add and review at least one question region" in body["confirmation_blockers"][0]
    elif mode == "structured_template":
        assert body["can_confirm"] is False
        assert (
            "Import and review at least one structured question"
            in body["confirmation_blockers"][0]
        )


def test_run_without_mode_defaults_to_assisted_pdf(client: TestClient) -> None:
    email = "preparation-default@kau.edu.sa"
    analysis_id = _make_ready_analysis(client, email)
    headers = auth_header(email)

    response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)

    assert response.status_code == 202, response.text
    assert _poll_until_terminal(client, analysis_id, headers)["state"] == "review_ready"
    review = client.get(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=headers,
    ).json()
    assert review["snapshot"]["preparation_mode"] == "assisted_pdf"
    assert review["snapshot"]["questions"]


def test_retry_preserves_selected_mode_when_failure_occurs_before_exam_extraction(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = stages.STAGE_HANDLERS[ProcessingStage.VALIDATING]
    calls = 0

    def fail_once(analysis: Analysis, session: object, settings: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("private validation failure")
        original(analysis, session, settings)

    monkeypatch.setitem(stages.STAGE_HANDLERS, ProcessingStage.VALIDATING, fail_once)
    email = "preparation-retry-manual@kau.edu.sa"
    analysis_id = _make_ready_analysis(client, email)
    headers = auth_header(email)

    started = client.post(
        f"/api/v1/analyses/{analysis_id}/run",
        headers=headers,
        json={"question_preparation_mode": "manual_pdf"},
    )
    assert started.status_code == 202
    assert _poll_until_terminal(client, analysis_id, headers)["state"] == "failed"

    retried = client.post(f"/api/v1/analyses/{analysis_id}/retry", headers=headers)
    assert retried.status_code == 202
    assert _poll_until_terminal(client, analysis_id, headers)["state"] == "review_ready"

    review = client.get(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=headers,
    ).json()
    assert review["snapshot"]["preparation_mode"] == "manual_pdf"
    assert review["snapshot"]["questions"] == []
