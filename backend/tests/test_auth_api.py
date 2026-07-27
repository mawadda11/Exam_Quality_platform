from __future__ import annotations

from fastapi.testclient import TestClient

REGISTER_PAYLOAD = {
    "email": "faculty@university.edu",
    "password": "StrongPassword2026",
    "display_name": "Dr Faculty",
    "institution": "Example University",
    "department": "Computing",
}


def test_register_returns_session_and_current_user(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "faculty@university.edu"
    assert body["user"]["user_type"] == "Faculty Member"

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["id"] == body["user"]["id"]


def test_duplicate_registration_is_rejected(client: TestClient) -> None:
    assert client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD).status_code == 201
    duplicate = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert duplicate.status_code == 409


def test_login_normalizes_email_and_rejects_wrong_password(client: TestClient) -> None:
    assert client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD).status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": " Faculty@University.EDU ", "password": "StrongPassword2026"},
    )
    assert login.status_code == 200

    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "WrongPassword2026"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Invalid email or password."


def test_password_policy_is_enforced(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "password": "short1"},
    )
    assert response.status_code == 422


def test_password_reset_is_generic_single_use_and_revokes_old_access_token(
    client: TestClient,
) -> None:
    registered = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD).json()
    old_access_token = registered["access_token"]

    requested = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": REGISTER_PAYLOAD["email"]},
    )
    assert requested.status_code == 200
    reset_token = requested.json()["debug_reset_token"]
    assert reset_token

    confirmed = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "NewStrongPassword2027"},
    )
    assert confirmed.status_code == 200

    reused = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "AnotherPassword2028"},
    )
    assert reused.status_code == 400

    old_me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"},
    )
    assert old_me.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "NewStrongPassword2027"},
    )
    assert new_login.status_code == 200


def test_password_reset_does_not_disclose_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "missing@university.edu"},
    )
    assert response.status_code == 200
    assert response.json()["debug_reset_token"] is None


def test_logout_revokes_issued_access_token(client: TestClient) -> None:
    registered = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD).json()
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_registered_faculty_accounts_are_strictly_isolated(client: TestClient) -> None:
    first = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD).json()
    second_payload = {
        **REGISTER_PAYLOAD,
        "email": "second@university.edu",
        "display_name": "Dr Second",
    }
    second = client.post("/api/v1/auth/register", json=second_payload).json()
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}

    created = client.post(
        "/api/v1/analyses",
        headers=first_headers,
        json={
            "course": {"code": "AUTH-101", "name": "Authentication Testing"},
            "exam_type": "Midterm",
            "term": "2026 Fall",
        },
    )
    assert created.status_code == 201
    analysis_id = created.json()["id"]

    assert client.get(f"/api/v1/analyses/{analysis_id}", headers=second_headers).status_code == 404
    assert client.get("/api/v1/analyses", headers=second_headers).json() == []
    assert len(client.get("/api/v1/analyses", headers=first_headers).json()) == 1
