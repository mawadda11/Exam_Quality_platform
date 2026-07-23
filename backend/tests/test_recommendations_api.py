from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from helpers import auth_header
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import AcademicStatus
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
) -> str:
    with Session(db_engine) as session:
        finding = Finding(
            analysis_id=uuid.UUID(analysis_id),
            requirement_id=requirement_id,
            rule_id=rule_id,
            status=status,
            explanation="test finding",
            confidence=1.0,
            evaluator_type="deterministic_rule",
        )
        session.add(finding)
        session.commit()
        return str(finding.id)


def test_recommendations_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _create_analysis(client, "rec-owner@kau.edu.sa")
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/recommendations",
        headers=auth_header("rec-intruder@kau.edu.sa"),
    )
    assert response.status_code == 404


def test_recommendations_missing_auth_header_returns_401(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "rec-auth@kau.edu.sa")
    response = client.get(f"/api/v1/analyses/{analysis_id}/recommendations")
    assert response.status_code == 401


def test_recommendations_empty_list_when_no_findings(client: TestClient) -> None:
    email = "rec-empty@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/recommendations", headers=auth_header(email)
    )
    assert response.status_code == 200
    assert response.json() == []


def test_satisfied_and_not_applicable_findings_produce_no_recommendation(
    client: TestClient, db_engine: Engine
) -> None:
    email = "rec-none@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ001", "RULE001", AcademicStatus.SATISFIED)
    _insert_finding(db_engine, analysis_id, "REQ018", "RULE018", AcademicStatus.NOT_APPLICABLE)

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/recommendations", headers=auth_header(email)
    )
    assert response.status_code == 200
    assert response.json() == []


def test_partially_satisfied_finding_returns_its_matching_recommendation(
    client: TestClient, db_engine: Engine
) -> None:
    email = "rec-partial@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    finding_id = _insert_finding(
        db_engine, analysis_id, "REQ001", "RULE001", AcademicStatus.PARTIALLY_SATISFIED
    )

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/recommendations", headers=auth_header(email)
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["finding_id"] == finding_id
    assert body[0]["requirement_id"] == "REQ001"
    assert body[0]["rule_id"] == "RULE001"
    assert body[0]["status"] == "Partially Satisfied"
    assert body[0]["recommendation_id"] == "REC001"
    assert body[0]["title"] == "Map the Question to a CLO"
    assert body[0]["target_user"] == "Faculty and Course Coordinator"
    assert body[0]["recommendation_type"] == "Corrective"


def test_not_verified_finding_returns_the_input_request_recommendation(
    client: TestClient, db_engine: Engine
) -> None:
    email = "rec-not-verified@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_finding(db_engine, analysis_id, "REQ001", "RULE001", AcademicStatus.NOT_VERIFIED)

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/recommendations", headers=auth_header(email)
    )
    body = response.json()
    assert len(body) == 1
    assert body[0]["recommendation_id"] == "REC031"
    assert body[0]["recommendation_type"] == "Input Request"


def test_multiple_findings_each_traceable_to_their_own_recommendation(
    client: TestClient, db_engine: Engine
) -> None:
    email = "rec-multi@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    first_id = _insert_finding(
        db_engine, analysis_id, "REQ001", "RULE001", AcademicStatus.NOT_SATISFIED
    )
    second_id = _insert_finding(
        db_engine, analysis_id, "REQ019", "RULE019", AcademicStatus.PARTIALLY_SATISFIED
    )

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/recommendations", headers=auth_header(email)
    )
    body = response.json()
    by_finding = {row["finding_id"]: row for row in body}
    assert len(body) == 2
    assert by_finding[first_id]["recommendation_id"] == "REC001"
    assert by_finding[second_id]["recommendation_id"] == "REC019"
