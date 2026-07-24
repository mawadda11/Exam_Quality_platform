from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from helpers import auth_header
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import AcademicStatus, ProcessingStage
from app.models.analysis import Analysis
from app.models.finding import Finding

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


def _insert_finding(
    db_engine: Engine, analysis_id: str, requirement_id: str, rule_id: str, status: AcademicStatus
) -> None:
    with Session(db_engine) as session:
        session.add(
            Finding(
                analysis_id=uuid.UUID(analysis_id),
                requirement_id=requirement_id,
                rule_id=rule_id,
                status=status,
                explanation="test finding",
                confidence=1.0,
                evaluator_type="deterministic_rule",
            )
        )
        session.commit()


def _mark_completed(db_engine: Engine, analysis_id: str) -> None:
    with Session(db_engine) as session:
        analysis = session.execute(
            select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
        ).scalar_one()
        analysis.state = ProcessingStage.COMPLETED
        session.commit()


def test_create_report_rejects_a_non_completed_analysis(client: TestClient) -> None:
    email = "report-not-done@kau.edu.sa"
    analysis_id = _create_analysis(client, email)

    response = client.post(f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email))
    assert response.status_code == 409


def test_create_report_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _create_analysis(client, "report-owner@kau.edu.sa")
    _mark_completed(db_engine, analysis_id)

    response = client.post(
        f"/api/v1/analyses/{analysis_id}/reports",
        headers=auth_header("report-intruder@kau.edu.sa"),
    )
    assert response.status_code == 404


def test_create_report_succeeds_for_a_completed_analysis(
    client: TestClient, db_engine: Engine
) -> None:
    email = "report-ok@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ001", "RULE001", AcademicStatus.SATISFIED)
    _insert_finding(db_engine, analysis_id, "REQ005", "RULE005", AcademicStatus.PARTIALLY_SATISFIED)
    _mark_completed(db_engine, analysis_id)

    response = client.post(f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email))
    assert response.status_code == 201
    body = response.json()

    assert body["analysis_id"] == analysis_id
    assert body["format"] == "pdf"
    assert body["kb_version"] == "1.0"
    assert body["denominator"] == 2
    assert body["score"] == "75.00"
    assert body["satisfied_count"] == 1
    assert body["partially_satisfied_count"] == 1
    assert body["size_bytes"] > 0
    assert "id" in body
    assert "created_at" in body


def test_regenerating_a_report_creates_a_new_record_not_a_replacement(
    client: TestClient, db_engine: Engine
) -> None:
    email = "report-regen@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ018", "RULE018", AcademicStatus.SATISFIED)
    _mark_completed(db_engine, analysis_id)

    first = client.post(f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email))
    second = client.post(f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email))
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]

    listing = client.get(f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email))
    assert listing.status_code == 200
    ids = [r["id"] for r in listing.json()]
    assert len(ids) == 2
    assert first.json()["id"] in ids
    assert second.json()["id"] in ids
    # Most recent first.
    assert listing.json()[0]["id"] == second.json()["id"]


def test_list_reports_empty_before_any_generation(client: TestClient, db_engine: Engine) -> None:
    email = "report-empty@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _mark_completed(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email))
    assert response.status_code == 200
    assert response.json() == []


def test_get_report_metadata(client: TestClient, db_engine: Engine) -> None:
    email = "report-meta@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ019", "RULE019", AcademicStatus.SATISFIED)
    _mark_completed(db_engine, analysis_id)

    created = client.post(
        f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email)
    ).json()

    response = client.get(f"/api/v1/reports/{created['id']}", headers=auth_header(email))
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["denominator"] == created["denominator"]


def test_get_report_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    email = "report-meta-owner@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ019", "RULE019", AcademicStatus.SATISFIED)
    _mark_completed(db_engine, analysis_id)
    created = client.post(
        f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email)
    ).json()

    response = client.get(
        f"/api/v1/reports/{created['id']}", headers=auth_header("report-meta-intruder@kau.edu.sa")
    )
    assert response.status_code == 404


def test_get_report_returns_404_for_unknown_id(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/reports/{uuid.uuid4()}", headers=auth_header("someone@kau.edu.sa")
    )
    assert response.status_code == 404


def test_download_report_returns_the_pdf_bytes(client: TestClient, db_engine: Engine) -> None:
    email = "report-download@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ018", "RULE018", AcademicStatus.SATISFIED)
    _mark_completed(db_engine, analysis_id)

    created = client.post(
        f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email)
    ).json()

    response = client.get(f"/api/v1/reports/{created['id']}/download", headers=auth_header(email))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert len(response.content) == created["size_bytes"]


def test_download_report_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    email = "report-dl-owner@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ018", "RULE018", AcademicStatus.SATISFIED)
    _mark_completed(db_engine, analysis_id)
    created = client.post(
        f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email)
    ).json()

    response = client.get(
        f"/api/v1/reports/{created['id']}/download",
        headers=auth_header("report-dl-intruder@kau.edu.sa"),
    )
    assert response.status_code == 404


def test_reports_endpoints_require_auth_header(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _create_analysis(client, "report-auth@kau.edu.sa")
    _mark_completed(db_engine, analysis_id)

    assert client.post(f"/api/v1/analyses/{analysis_id}/reports").status_code == 401
    assert client.get(f"/api/v1/analyses/{analysis_id}/reports").status_code == 401
    assert client.get(f"/api/v1/reports/{uuid.uuid4()}").status_code == 401
    assert client.get(f"/api/v1/reports/{uuid.uuid4()}/download").status_code == 401
