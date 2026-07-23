from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from helpers import auth_header
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.question import Question

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


def _insert_questions(db_engine: Engine, analysis_id: str) -> None:
    # Inserted out of sequence order on purpose, to prove the endpoint sorts.
    with Session(db_engine) as session:
        session.add_all(
            [
                Question(
                    analysis_id=uuid.UUID(analysis_id),
                    number_label="Q2",
                    question_text="Second question",
                    page_number=1,
                    marks=None,
                    sequence=2,
                    confidence=1.0,
                ),
                Question(
                    analysis_id=uuid.UUID(analysis_id),
                    number_label="Q1",
                    question_text="First question",
                    page_number=1,
                    marks=5.0,
                    sequence=1,
                    confidence=1.0,
                    geometry={"x0": 1.0, "top": 2.0, "x1": 3.0, "bottom": 4.0},
                ),
            ]
        )
        session.commit()


def test_questions_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _create_analysis(client, "owner@kau.edu.sa")
    _insert_questions(db_engine, analysis_id)

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/questions", headers=auth_header("intruder@kau.edu.sa")
    )
    assert response.status_code == 404


def test_questions_returns_404_for_unknown_analysis(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/analyses/{uuid.uuid4()}/questions", headers=auth_header("someone@kau.edu.sa")
    )
    assert response.status_code == 404


def test_questions_missing_auth_header_returns_401(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "auth@kau.edu.sa")
    response = client.get(f"/api/v1/analyses/{analysis_id}/questions")
    assert response.status_code == 401


def test_questions_returned_in_sequence_order(client: TestClient, db_engine: Engine) -> None:
    email = "order@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_questions(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/questions", headers=auth_header(email))
    assert response.status_code == 200
    body = response.json()
    assert [q["number_label"] for q in body] == ["Q1", "Q2"]
    assert [q["sequence"] for q in body] == [1, 2]


def test_questions_response_schema_fields(client: TestClient, db_engine: Engine) -> None:
    email = "schema@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_questions(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/questions", headers=auth_header(email))
    body = response.json()
    q1 = next(q for q in body if q["number_label"] == "Q1")

    assert q1["analysis_id"] == analysis_id
    assert q1["parent_question_id"] is None
    assert q1["question_text"] == "First question"
    assert q1["page_number"] == 1
    assert q1["marks"] == 5.0
    assert q1["confidence"] == 1.0
    assert q1["geometry"] == {"x0": 1.0, "top": 2.0, "x1": 3.0, "bottom": 4.0}
    assert "id" in q1
    assert "created_at" in q1


def test_questions_empty_list_when_none_extracted_yet(client: TestClient) -> None:
    email = "empty@kau.edu.sa"
    analysis_id = _create_analysis(client, email)

    response = client.get(f"/api/v1/analyses/{analysis_id}/questions", headers=auth_header(email))
    assert response.status_code == 200
    assert response.json() == []
