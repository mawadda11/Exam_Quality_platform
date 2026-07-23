from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from helpers import auth_header
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.topic import Topic

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


def _insert_clos(db_engine: Engine, analysis_id: str) -> None:
    with Session(db_engine) as session:
        session.add_all(
            [
                Clo(
                    analysis_id=uuid.UUID(analysis_id),
                    code="CLO2",
                    text="Second",
                    program_outcome_reference=None,
                    page_number=2,
                    confidence=1.0,
                ),
                Clo(
                    analysis_id=uuid.UUID(analysis_id),
                    code="CLO1",
                    text="First",
                    program_outcome_reference="PLO2",
                    page_number=1,
                    confidence=1.0,
                    geometry={"x0": 1.0, "top": 2.0, "x1": 3.0, "bottom": 4.0},
                ),
            ]
        )
        session.commit()


def _insert_topics(db_engine: Engine, analysis_id: str) -> None:
    with Session(db_engine) as session:
        session.add_all(
            [
                Topic(
                    analysis_id=uuid.UUID(analysis_id),
                    code="T2",
                    text="Second topic",
                    expected_hours=4.0,
                    page_number=2,
                    confidence=1.0,
                ),
                Topic(
                    analysis_id=uuid.UUID(analysis_id),
                    code="T1",
                    text="First topic",
                    expected_hours=3.0,
                    page_number=1,
                    confidence=1.0,
                ),
            ]
        )
        session.commit()


def _insert_assessment_records(db_engine: Engine, analysis_id: str) -> None:
    with Session(db_engine) as session:
        session.add_all(
            [
                AssessmentRecord(
                    analysis_id=uuid.UUID(analysis_id),
                    method="Final Exam",
                    activity="Written Exam",
                    percentage=30.0,
                    page_number=2,
                    confidence=1.0,
                ),
                AssessmentRecord(
                    analysis_id=uuid.UUID(analysis_id),
                    method="Midterm Exam",
                    activity="Written Exam",
                    percentage=20.0,
                    page_number=1,
                    confidence=1.0,
                ),
            ]
        )
        session.commit()


# --- /clos ---------------------------------------------------------------


def test_clos_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _create_analysis(client, "clo-owner@kau.edu.sa")
    _insert_clos(db_engine, analysis_id)
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/clos", headers=auth_header("clo-intruder@kau.edu.sa")
    )
    assert response.status_code == 404


def test_clos_returns_404_for_unknown_analysis(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/analyses/{uuid.uuid4()}/clos", headers=auth_header("someone@kau.edu.sa")
    )
    assert response.status_code == 404


def test_clos_missing_auth_header_returns_401(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "clo-auth@kau.edu.sa")
    response = client.get(f"/api/v1/analyses/{analysis_id}/clos")
    assert response.status_code == 401


def test_clos_returned_in_deterministic_page_order(client: TestClient, db_engine: Engine) -> None:
    email = "clo-order@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_clos(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/clos", headers=auth_header(email))
    assert response.status_code == 200
    body = response.json()
    assert [c["code"] for c in body] == ["CLO1", "CLO2"]


def test_clos_response_schema_fields(client: TestClient, db_engine: Engine) -> None:
    email = "clo-schema@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_clos(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/clos", headers=auth_header(email))
    clo1 = next(c for c in response.json() if c["code"] == "CLO1")
    assert clo1["analysis_id"] == analysis_id
    assert clo1["text"] == "First"
    assert clo1["program_outcome_reference"] == "PLO2"
    assert clo1["page_number"] == 1
    assert clo1["confidence"] == 1.0
    assert clo1["geometry"] == {"x0": 1.0, "top": 2.0, "x1": 3.0, "bottom": 4.0}
    assert "id" in clo1
    assert "created_at" in clo1
    # Raw extracted source data only - no mapping/coverage/status/score fields.
    assert "status" not in clo1
    assert "coverage" not in clo1
    assert "score" not in clo1


def test_clos_empty_list_when_none_extracted_yet(client: TestClient) -> None:
    email = "clo-empty@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    response = client.get(f"/api/v1/analyses/{analysis_id}/clos", headers=auth_header(email))
    assert response.status_code == 200
    assert response.json() == []


# --- /topics ---------------------------------------------------------------


def test_topics_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _create_analysis(client, "topic-owner@kau.edu.sa")
    _insert_topics(db_engine, analysis_id)
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/topics", headers=auth_header("topic-intruder@kau.edu.sa")
    )
    assert response.status_code == 404


def test_topics_missing_auth_header_returns_401(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "topic-auth@kau.edu.sa")
    response = client.get(f"/api/v1/analyses/{analysis_id}/topics")
    assert response.status_code == 401


def test_topics_returned_in_deterministic_page_order(client: TestClient, db_engine: Engine) -> None:
    email = "topic-order@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_topics(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/topics", headers=auth_header(email))
    assert response.status_code == 200
    body = response.json()
    assert [t["code"] for t in body] == ["T1", "T2"]
    assert [t["expected_hours"] for t in body] == [3.0, 4.0]


def test_topics_response_schema_fields(client: TestClient, db_engine: Engine) -> None:
    email = "topic-schema@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_topics(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/topics", headers=auth_header(email))
    t1 = next(t for t in response.json() if t["code"] == "T1")
    assert t1["text"] == "First topic"
    assert t1["expected_hours"] == 3.0
    assert t1["page_number"] == 1
    assert "status" not in t1
    assert "coverage" not in t1


def test_topics_empty_list_when_none_extracted_yet(client: TestClient) -> None:
    email = "topic-empty@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    response = client.get(f"/api/v1/analyses/{analysis_id}/topics", headers=auth_header(email))
    assert response.status_code == 200
    assert response.json() == []


# --- /assessment-records ----------------------------------------------------


def test_assessment_records_returns_404_for_non_owner(
    client: TestClient, db_engine: Engine
) -> None:
    analysis_id = _create_analysis(client, "ar-owner@kau.edu.sa")
    _insert_assessment_records(db_engine, analysis_id)
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/assessment-records",
        headers=auth_header("ar-intruder@kau.edu.sa"),
    )
    assert response.status_code == 404


def test_assessment_records_missing_auth_header_returns_401(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "ar-auth@kau.edu.sa")
    response = client.get(f"/api/v1/analyses/{analysis_id}/assessment-records")
    assert response.status_code == 401


def test_assessment_records_returned_in_deterministic_page_order(
    client: TestClient, db_engine: Engine
) -> None:
    email = "ar-order@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_assessment_records(db_engine, analysis_id)

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/assessment-records", headers=auth_header(email)
    )
    assert response.status_code == 200
    body = response.json()
    assert [r["method"] for r in body] == ["Midterm Exam", "Final Exam"]


def test_assessment_records_response_schema_fields(client: TestClient, db_engine: Engine) -> None:
    email = "ar-schema@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_assessment_records(db_engine, analysis_id)

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/assessment-records", headers=auth_header(email)
    )
    midterm = next(r for r in response.json() if r["method"] == "Midterm Exam")
    assert midterm["activity"] == "Written Exam"
    assert midterm["percentage"] == 20.0
    assert midterm["page_number"] == 1
    assert "status" not in midterm
    assert "coverage" not in midterm


def test_assessment_records_empty_list_when_none_extracted_yet(client: TestClient) -> None:
    email = "ar-empty@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/assessment-records", headers=auth_header(email)
    )
    assert response.status_code == 200
    assert response.json() == []
