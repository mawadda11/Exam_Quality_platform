from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from helpers import auth_header

VALID_ANALYSIS_PAYLOAD = {
    "course": {"code": "cpit-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}


def test_create_analysis_returns_201_with_expected_shape(client: TestClient) -> None:
    response = client.post(
        "/api/v1/analyses", json=VALID_ANALYSIS_PAYLOAD, headers=auth_header("prof.a@kau.edu.sa")
    )

    assert response.status_code == 201
    body = response.json()
    assert body["course"]["code"] == "CPIT-450"
    assert body["state"] == "queued"
    assert body["exam_uploaded"] is False
    assert body["tp153_uploaded"] is False
    assert body["ready_for_analysis"] is False
    assert body["uploaded_files"] == []


def test_create_analysis_missing_auth_header_returns_401(client: TestClient) -> None:
    response = client.post("/api/v1/analyses", json=VALID_ANALYSIS_PAYLOAD)
    assert response.status_code == 401


def test_create_analysis_malformed_auth_header_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/analyses",
        json=VALID_ANALYSIS_PAYLOAD,
        headers={"X-Dev-User-Email": "not-an-email"},
    )
    assert response.status_code == 401


def test_create_analysis_reuses_existing_course_by_code(client: TestClient) -> None:
    headers = auth_header("prof.b@kau.edu.sa")
    first = client.post("/api/v1/analyses", json=VALID_ANALYSIS_PAYLOAD, headers=headers)
    second_payload = {
        **VALID_ANALYSIS_PAYLOAD,
        "course": {"code": "CPIT-450", "name": "Different Name"},
    }

    second = client.post("/api/v1/analyses", json=second_payload, headers=headers)

    assert first.json()["course"]["id"] == second.json()["course"]["id"]
    assert second.json()["course"]["name"] == "Software Engineering"


def test_create_analysis_invalid_exam_type_returns_422(client: TestClient) -> None:
    payload = {**VALID_ANALYSIS_PAYLOAD, "exam_type": "Quiz"}
    response = client.post(
        "/api/v1/analyses", json=payload, headers=auth_header("prof.c@kau.edu.sa")
    )
    assert response.status_code == 422


def test_create_analysis_missing_term_returns_422(client: TestClient) -> None:
    payload = {"course": VALID_ANALYSIS_PAYLOAD["course"], "exam_type": "Midterm"}
    response = client.post(
        "/api/v1/analyses", json=payload, headers=auth_header("prof.d@kau.edu.sa")
    )
    assert response.status_code == 422


def test_list_analyses_only_returns_callers_own(client: TestClient) -> None:
    client.post(
        "/api/v1/analyses", json=VALID_ANALYSIS_PAYLOAD, headers=auth_header("owner@kau.edu.sa")
    )

    other_response = client.get("/api/v1/analyses", headers=auth_header("someone-else@kau.edu.sa"))
    assert other_response.status_code == 200
    assert other_response.json() == []

    own_response = client.get("/api/v1/analyses", headers=auth_header("owner@kau.edu.sa"))
    assert len(own_response.json()) == 1


def test_get_analysis_not_owned_returns_404(client: TestClient) -> None:
    create = client.post(
        "/api/v1/analyses", json=VALID_ANALYSIS_PAYLOAD, headers=auth_header("owner2@kau.edu.sa")
    )
    analysis_id = create.json()["id"]

    response = client.get(
        f"/api/v1/analyses/{analysis_id}", headers=auth_header("intruder@kau.edu.sa")
    )
    assert response.status_code == 404


def test_get_analysis_invalid_uuid_returns_422(client: TestClient) -> None:
    response = client.get("/api/v1/analyses/not-a-uuid", headers=auth_header("owner3@kau.edu.sa"))
    assert response.status_code == 422


def test_get_analysis_nonexistent_uuid_returns_404(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/analyses/{uuid.uuid4()}", headers=auth_header("owner4@kau.edu.sa")
    )
    assert response.status_code == 404


def test_repeated_header_email_maps_to_same_user(client: TestClient) -> None:
    headers = auth_header("same-user@kau.edu.sa")
    first = client.post("/api/v1/analyses", json=VALID_ANALYSIS_PAYLOAD, headers=headers)
    second = client.post("/api/v1/analyses", json=VALID_ANALYSIS_PAYLOAD, headers=headers)

    assert first.json()["owner_user_id"] == second.json()["owner_user_id"]
