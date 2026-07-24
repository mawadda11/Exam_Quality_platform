"""Unit tests for app.core.errors' three exception handlers, plus one
integration test proving handle_unexpected_exception is actually wired into
the running app (registration order doesn't matter for the first two -
FastAPI/Starlette resolve handlers most-specific-first - but the wiring
itself is worth proving end-to-end once).
"""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.errors import (
    UNEXPECTED_ERROR_MESSAGE,
    handle_http_exception,
    handle_unexpected_exception,
    handle_validation_error,
    register_exception_handlers,
)


def _request(path: str = "/api/v1/analyses", method: str = "GET") -> Request:
    return Request(
        {"type": "http", "method": method, "path": path, "headers": [], "query_string": b""}
    )


def _body(response) -> dict:  # type: ignore[no-untyped-def]
    return json.loads(response.body)


# --- Unit tests: each handler in isolation, no HTTP layer -----------------


def test_handle_http_exception_preserves_status_and_detail() -> None:
    exc = HTTPException(status_code=404, detail="Analysis not found.")
    response = asyncio.run(handle_http_exception(_request(), exc))

    assert response.status_code == 404
    assert _body(response) == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "Analysis not found.",
    }


def test_handle_validation_error_returns_422_with_error_list() -> None:
    exc = RequestValidationError(errors=[{"loc": ("body", "term"), "msg": "field required"}])
    response = asyncio.run(handle_validation_error(_request(), exc))

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "field required" in _body(response)["detail"]


def test_handle_unexpected_exception_returns_safe_generic_500() -> None:
    exc = RuntimeError("sensitive internal detail: /etc/secret-config")
    response = asyncio.run(handle_unexpected_exception(_request(), exc))

    assert response.status_code == 500
    body = _body(response)
    assert body["detail"] == UNEXPECTED_ERROR_MESSAGE
    assert "sensitive internal detail" not in json.dumps(body)
    assert "/etc/secret-config" not in json.dumps(body)


def test_handle_unexpected_exception_response_never_contains_the_original_message() -> None:
    # A slightly different flavor of the same guarantee, parametrized over
    # a message shaped like something genuinely sensitive (a DB DSN with a
    # password) - proves the safety property doesn't depend on the exact
    # wording of any one test exception.
    exc = ValueError("connection failed: postgresql://exam_quality:hunter2@db/exam_quality")
    response = asyncio.run(handle_unexpected_exception(_request(), exc))

    assert response.status_code == 500
    assert "hunter2" not in json.dumps(_body(response))


# --- Integration test: proves the handler is actually wired into the app --


def test_unhandled_exception_from_a_real_request_returns_safe_problem_details() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("sensitive internal detail: should never reach the client")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": UNEXPECTED_ERROR_MESSAGE,
    }
    assert "sensitive internal detail" not in response.text
