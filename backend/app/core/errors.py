from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Never expose exception details to the client - only this fixed, generic
# message, matching the same safe-failure pattern already used for
# background pipeline errors (app.services.processing.runner.SAFE_FAILURE_MESSAGE).
# Full details go to the server-side log only (see handle_unexpected_exception).
UNEXPECTED_ERROR_MESSAGE = "An unexpected error occurred. Please try again later."


def _problem_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "type": "about:blank",
            "title": HTTPStatus(status_code).phrase,
            "status": status_code,
            "detail": detail,
        },
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    return _problem_response(exc.status_code, str(exc.detail))


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _problem_response(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc.errors()))


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    """Catches anything not already handled by a more specific handler above
    (HTTPException/RequestValidationError still route to those - FastAPI/
    Starlette resolve handlers most-specific-first, regardless of
    registration order). Without this, an uncaught exception falls through
    to the ASGI server's own default handling, which is not guaranteed to
    honor this project's "never leak exception details" rule and produces
    an inconsistent (non-Problem-Details) response shape.

    Logs method/path only (safe metadata, per docs/SECURITY_AND_PRIVACY.md's
    "Log IDs, stages, durations, error classes, and safe summaries") -
    never the request body, headers, or query string, which could contain
    exam/TP-153 content or credentials."""
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    return _problem_response(status.HTTP_500_INTERNAL_SERVER_ERROR, UNEXPECTED_ERROR_MESSAGE)


def register_exception_handlers(app: FastAPI) -> None:
    # Module-level handler functions (not defined inline here) so each one
    # is independently importable and unit-testable - see test_errors.py.
    # `app.exception_handler(exc_type)` (called directly, rather than as a
    # decorator) is used instead of `add_exception_handler` because the
    # latter's type stubs reject a handler typed against a specific
    # exception subclass rather than the base `Exception`.
    app.exception_handler(HTTPException)(handle_http_exception)
    app.exception_handler(RequestValidationError)(handle_validation_error)
    app.exception_handler(Exception)(handle_unexpected_exception)
