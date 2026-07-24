from __future__ import annotations

import io
import uuid

from fastapi.testclient import TestClient
from helpers import auth_header, valid_pdf_bytes
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import ProcessingStage
from app.models.analysis import Analysis

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


def _upload(client: TestClient, analysis_id: str, email: str, file_type: str) -> None:
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/files",
        headers=auth_header(email),
        data={"file_type": file_type},
        files={"file": (f"{file_type}.pdf", io.BytesIO(valid_pdf_bytes()), "application/pdf")},
    )
    assert response.status_code == 201


def _mark_completed(db_engine: Engine, analysis_id: str) -> None:
    with Session(db_engine) as session:
        analysis = session.execute(
            select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
        ).scalar_one()
        analysis.state = ProcessingStage.COMPLETED
        session.commit()


def _completed_analysis_with_both_files(client: TestClient, db_engine: Engine, email: str) -> str:
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam")
    _upload(client, analysis_id, email, "tp153")
    _mark_completed(db_engine, analysis_id)
    return analysis_id


def test_reanalysis_rejects_a_non_completed_predecessor(client: TestClient) -> None:
    email = "reanalysis-not-done@kau.edu.sa"
    analysis_id = _create_analysis(client, email)

    response = client.post(f"/api/v1/analyses/{analysis_id}/reanalysis", headers=auth_header(email))
    assert response.status_code == 409


def test_reanalysis_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _completed_analysis_with_both_files(
        client, db_engine, "reanalysis-owner@kau.edu.sa"
    )

    response = client.post(
        f"/api/v1/analyses/{analysis_id}/reanalysis",
        headers=auth_header("reanalysis-intruder@kau.edu.sa"),
    )
    assert response.status_code == 404


def test_reanalysis_creates_a_new_linked_analysis_inheriting_course_and_term(
    client: TestClient, db_engine: Engine
) -> None:
    email = "reanalysis-basic@kau.edu.sa"
    predecessor_id = _completed_analysis_with_both_files(client, db_engine, email)

    response = client.post(
        f"/api/v1/analyses/{predecessor_id}/reanalysis", headers=auth_header(email)
    )
    assert response.status_code == 201
    body = response.json()

    assert body["id"] != predecessor_id
    assert body["predecessor_analysis_id"] == predecessor_id
    assert body["course"]["code"] == "CPIT-450"
    assert body["exam_type"] == "Midterm"
    assert body["term"] == "2026 Spring"
    assert body["state"] == "queued"


def test_reanalysis_never_replaces_the_predecessor(client: TestClient, db_engine: Engine) -> None:
    email = "reanalysis-preserve@kau.edu.sa"
    predecessor_id = _completed_analysis_with_both_files(client, db_engine, email)

    client.post(f"/api/v1/analyses/{predecessor_id}/reanalysis", headers=auth_header(email))

    predecessor_after = client.get(f"/api/v1/analyses/{predecessor_id}", headers=auth_header(email))
    assert predecessor_after.status_code == 200
    assert predecessor_after.json()["state"] == "completed"

    history = client.get("/api/v1/analyses", headers=auth_header(email))
    assert history.status_code == 200
    assert len(history.json()) == 2


def test_reuse_tp153_defaults_true_and_copies_the_predecessor_file(
    client: TestClient, db_engine: Engine
) -> None:
    email = "reanalysis-reuse@kau.edu.sa"
    predecessor_id = _completed_analysis_with_both_files(client, db_engine, email)

    created = client.post(
        f"/api/v1/analyses/{predecessor_id}/reanalysis", headers=auth_header(email)
    ).json()
    assert created["tp153_uploaded"] is True
    assert created["exam_uploaded"] is False
    assert created["ready_for_analysis"] is False

    # Only the revised exam still needs uploading - matches the M10 decision
    # that the exam must always be freshly uploaded.
    _upload(client, created["id"], email, "exam")
    refreshed = client.get(f"/api/v1/analyses/{created['id']}", headers=auth_header(email))
    assert refreshed.json()["ready_for_analysis"] is True


def test_reuse_tp153_false_requires_a_fresh_tp153_upload_too(
    client: TestClient, db_engine: Engine
) -> None:
    email = "reanalysis-fresh@kau.edu.sa"
    predecessor_id = _completed_analysis_with_both_files(client, db_engine, email)

    created = client.post(
        f"/api/v1/analyses/{predecessor_id}/reanalysis",
        headers=auth_header(email),
        json={"reuse_tp153": False},
    ).json()
    assert created["tp153_uploaded"] is False

    _upload(client, created["id"], email, "exam")
    after_exam_only = client.get(
        f"/api/v1/analyses/{created['id']}", headers=auth_header(email)
    ).json()
    assert after_exam_only["ready_for_analysis"] is False

    _upload(client, created["id"], email, "tp153")
    after_both = client.get(f"/api/v1/analyses/{created['id']}", headers=auth_header(email)).json()
    assert after_both["ready_for_analysis"] is True


def test_reused_tp153_is_a_distinct_copy_not_a_shared_storage_key(
    client: TestClient, db_engine: Engine
) -> None:
    email = "reanalysis-copy@kau.edu.sa"
    predecessor_id = _completed_analysis_with_both_files(client, db_engine, email)

    predecessor = client.get(
        f"/api/v1/analyses/{predecessor_id}", headers=auth_header(email)
    ).json()
    predecessor_tp153 = next(f for f in predecessor["uploaded_files"] if f["file_type"] == "tp153")

    created = client.post(
        f"/api/v1/analyses/{predecessor_id}/reanalysis", headers=auth_header(email)
    ).json()
    new_tp153 = next(f for f in created["uploaded_files"] if f["file_type"] == "tp153")

    assert new_tp153["id"] != predecessor_tp153["id"]
    assert new_tp153["sha256_hash"] == predecessor_tp153["sha256_hash"]
    assert new_tp153["size_bytes"] == predecessor_tp153["size_bytes"]


def test_reanalysis_requires_auth_header(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _completed_analysis_with_both_files(
        client, db_engine, "reanalysis-auth@kau.edu.sa"
    )
    response = client.post(f"/api/v1/analyses/{analysis_id}/reanalysis")
    assert response.status_code == 401
