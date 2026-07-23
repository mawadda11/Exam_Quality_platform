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


def _finding(analysis_id: str, rule_id: str, status: AcademicStatus) -> Finding:
    return Finding(
        analysis_id=uuid.UUID(analysis_id),
        requirement_id=rule_id.replace("RULE", "REQ"),
        rule_id=rule_id,
        status=status,
        explanation="test finding",
        confidence=1.0,
        evaluator_type="deterministic_rule",
    )


def _insert_mixed_findings(db_engine: Engine, analysis_id: str) -> None:
    with Session(db_engine) as session:
        session.add_all(
            [
                _finding(analysis_id, "RULE001", AcademicStatus.SATISFIED),
                _finding(analysis_id, "RULE005", AcademicStatus.PARTIALLY_SATISFIED),
                _finding(analysis_id, "RULE007", AcademicStatus.NOT_SATISFIED),
                _finding(analysis_id, "RULE009", AcademicStatus.NOT_VERIFIED),
                _finding(analysis_id, "RULE018", AcademicStatus.NOT_APPLICABLE),
            ]
        )
        session.commit()


def test_score_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _create_analysis(client, "score-owner@kau.edu.sa")
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/score",
        headers=auth_header("score-intruder@kau.edu.sa"),
    )
    assert response.status_code == 404


def test_score_returns_404_for_unknown_analysis(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/analyses/{uuid.uuid4()}/score", headers=auth_header("someone@kau.edu.sa")
    )
    assert response.status_code == 404


def test_score_missing_auth_header_returns_401(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "score-auth@kau.edu.sa")
    response = client.get(f"/api/v1/analyses/{analysis_id}/score")
    assert response.status_code == 401


def test_score_is_insufficient_evidence_before_rules_run(client: TestClient) -> None:
    email = "score-empty@kau.edu.sa"
    analysis_id = _create_analysis(client, email)

    response = client.get(f"/api/v1/analyses/{analysis_id}/score", headers=auth_header(email))
    assert response.status_code == 200
    body = response.json()
    assert body["score"] is None
    assert body["label"] == "Insufficient Evidence"
    assert body["denominator"] == 0
    assert body["satisfied_count"] == 0
    assert body["partially_satisfied_count"] == 0
    assert body["not_satisfied_count"] == 0
    assert body["not_verified_count"] == 0
    assert body["not_applicable_count"] == 0


def test_score_computes_from_mixed_findings_and_counts_every_status(
    client: TestClient, db_engine: Engine
) -> None:
    email = "score-mixed@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_mixed_findings(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/score", headers=auth_header(email))
    assert response.status_code == 200
    body = response.json()

    # Satisfied(1.0) + Partially Satisfied(0.5) + Not Satisfied(0.0) = 1.5 / 3 * 100 = 50.00
    # Not Verified and Not Applicable are excluded from the denominator but
    # still individually counted (SCORE023/SCORE024).
    assert body["score"] == "50.00"
    assert body["label"] is None
    assert body["denominator"] == 3
    assert body["satisfied_count"] == 1
    assert body["partially_satisfied_count"] == 1
    assert body["not_satisfied_count"] == 1
    assert body["not_verified_count"] == 1
    assert body["not_applicable_count"] == 1
