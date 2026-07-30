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
from app.models.report import Report

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
    assert body["language"] == "en"
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


def test_legacy_completed_analysis_without_confirmation_remains_readable_and_downloadable(
    client: TestClient, db_engine: Engine
) -> None:
    email = "report-download@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ018", "RULE018", AcademicStatus.SATISFIED)
    _mark_completed(db_engine, analysis_id)

    created = client.post(
        f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email)
    ).json()

    analysis_response = client.get(f"/api/v1/analyses/{analysis_id}", headers=auth_header(email))
    response = client.get(f"/api/v1/reports/{created['id']}/download", headers=auth_header(email))
    assert analysis_response.status_code == 200
    assert analysis_response.json()["state"] == "completed"
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


def test_create_report_accepts_arabic_presentation_language(
    client: TestClient, db_engine: Engine
) -> None:
    email = "report-arabic@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ018", "RULE018", AcademicStatus.SATISFIED)
    _mark_completed(db_engine, analysis_id)

    created = client.post(
        f"/api/v1/analyses/{analysis_id}/reports",
        headers=auth_header(email),
        json={"language": "ar"},
    )
    assert created.status_code == 201
    assert created.json()["language"] == "ar"

    listing = client.get(f"/api/v1/analyses/{analysis_id}/reports", headers=auth_header(email))
    assert listing.status_code == 200
    assert listing.json()[0]["language"] == "ar"

    downloaded = client.get(
        f"/api/v1/reports/{created.json()['id']}/download",
        headers=auth_header(email),
    )
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"%PDF")


def test_create_report_rejects_unsupported_language(client: TestClient, db_engine: Engine) -> None:
    email = "report-language-invalid@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _mark_completed(db_engine, analysis_id)

    response = client.post(
        f"/api/v1/analyses/{analysis_id}/reports",
        headers=auth_header(email),
        json={"language": "fr"},
    )
    assert response.status_code == 422


def test_report_library_is_bounded_and_owner_filtered(
    client: TestClient, db_engine: Engine
) -> None:
    owner_email = "library-owner@kau.edu.sa"
    owner_analysis = _create_analysis(client, owner_email)
    _insert_finding(
        db_engine,
        owner_analysis,
        "REQ018",
        "RULE018",
        AcademicStatus.SATISFIED,
    )
    _mark_completed(db_engine, owner_analysis)
    owner_report = client.post(
        f"/api/v1/analyses/{owner_analysis}/reports",
        headers=auth_header(owner_email),
    )
    assert owner_report.status_code == 201

    no_report_analysis = client.post(
        "/api/v1/analyses",
        headers=auth_header(owner_email),
        json={
            "course": {"code": "CPIT-451", "name": "Secure Systems"},
            "exam_type": "Final",
            "term": "2026 Spring",
        },
    )
    assert no_report_analysis.status_code == 201
    _mark_completed(db_engine, no_report_analysis.json()["id"])

    incomplete_analysis = client.post(
        "/api/v1/analyses",
        headers=auth_header(owner_email),
        json={
            "course": {"code": "CPIT-452", "name": "Incomplete Systems"},
            "exam_type": "Midterm",
            "term": "2026 Spring",
        },
    )
    assert incomplete_analysis.status_code == 201

    intruder_email = "library-intruder@kau.edu.sa"
    intruder_analysis = client.post(
        "/api/v1/analyses",
        headers=auth_header(intruder_email),
        json={
            "course": {"code": "CPIT-499", "name": "Private Capstone"},
            "exam_type": "Final",
            "term": "2026 Spring",
        },
    )
    assert intruder_analysis.status_code == 201

    response = client.get(
        "/api/v1/reports?page=1&page_size=1",
        headers=auth_header(owner_email),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total_pages"] == 2
    assert len(body["items"]) == 1

    all_owner_items = client.get(
        "/api/v1/reports?page=1&page_size=12",
        headers=auth_header(owner_email),
    ).json()["items"]
    assert {item["analysis"]["id"] for item in all_owner_items} == {
        owner_analysis,
        no_report_analysis.json()["id"],
    }
    assert {item["status"] for item in all_owner_items} == {
        "available",
        "not_generated",
    }
    assert all("owner_user_id" not in item["analysis"] for item in all_owner_items)
    assert all("storage_key" not in (item["report"] or {}) for item in all_owner_items)
    assert incomplete_analysis.json()["id"] not in {
        item["analysis"]["id"] for item in all_owner_items
    }
    assert "Incomplete Systems" not in str(all_owner_items)
    assert "Private Capstone" not in str(all_owner_items)


def test_report_library_filters_searches_sorts_and_identifies_outdated_snapshots(
    client: TestClient, db_engine: Engine
) -> None:
    email = "library-filter@kau.edu.sa"
    first_analysis = _create_analysis(client, email)
    _insert_finding(
        db_engine,
        first_analysis,
        "REQ018",
        "RULE018",
        AcademicStatus.SATISFIED,
    )
    _mark_completed(db_engine, first_analysis)
    english_report = client.post(
        f"/api/v1/analyses/{first_analysis}/reports",
        headers=auth_header(email),
    )
    assert english_report.status_code == 201

    second_analysis_response = client.post(
        "/api/v1/analyses",
        headers=auth_header(email),
        json={
            "course": {"code": "ACCT-210", "name": "Accounting Systems"},
            "exam_type": "Final",
            "term": "2026 Fall",
        },
    )
    second_analysis = second_analysis_response.json()["id"]
    _insert_finding(
        db_engine,
        second_analysis,
        "REQ019",
        "RULE019",
        AcademicStatus.NOT_VERIFIED,
    )
    _mark_completed(db_engine, second_analysis)
    arabic_report = client.post(
        f"/api/v1/analyses/{second_analysis}/reports",
        headers=auth_header(email),
        json={"language": "ar"},
    )
    assert arabic_report.status_code == 201

    with Session(db_engine) as session:
        report = session.execute(
            select(Report).where(Report.id == uuid.UUID(english_report.json()["id"]))
        ).scalar_one()
        report.capability_version = "older-capability"
        session.commit()

    outdated = client.get(
        "/api/v1/reports?status=outdated",
        headers=auth_header(email),
    )
    assert outdated.status_code == 200
    assert outdated.json()["total"] == 1
    assert outdated.json()["items"][0]["report"]["id"] == english_report.json()["id"]
    assert outdated.json()["items"][0]["status"] == "outdated"

    insufficient = client.get(
        "/api/v1/reports?status=insufficient_evidence&language=ar&exam_type=Final",
        headers=auth_header(email),
    )
    assert insufficient.status_code == 200
    assert insufficient.json()["total"] == 1
    assert insufficient.json()["items"][0]["report"]["id"] == arabic_report.json()["id"]
    assert insufficient.json()["items"][0]["status"] == "insufficient_evidence"

    searched = client.get(
        f"/api/v1/reports?q={arabic_report.json()['id']}&sort=course",
        headers=auth_header(email),
    )
    assert searched.status_code == 200
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["analysis"]["course_name"] == "Accounting Systems"


def test_report_library_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/reports").status_code == 401
