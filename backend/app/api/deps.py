from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.identity import IdentityError, resolve_faculty_user
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.report import Report
from app.models.user import User
from app.services.auth.tokens import AccessTokenError, decode_access_token

_bearer = HTTPBearer(auto_error=False)


def _authentication_error(detail: str = "Authentication required.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _authentication_error()
    try:
        claims = decode_access_token(credentials.credentials, settings)
        return resolve_faculty_user(db, claims, settings)
    except (AccessTokenError, IdentityError):
        raise _authentication_error("Invalid or expired access token.") from None


def get_owned_analysis(
    analysis_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Analysis:
    statement = select(Analysis).where(
        Analysis.id == analysis_id, Analysis.user_id == current_user.id
    )
    analysis = db.execute(statement).scalar_one_or_none()
    if analysis is None:
        # Same response for "doesn't exist" and "belongs to someone else" - avoids
        # confirming a resource's existence to a non-owner (IDOR mitigation).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    return analysis


def get_owned_report(
    report_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Report:
    statement = (
        select(Report)
        .join(Analysis, Report.analysis_id == Analysis.id)
        .where(Report.id == report_id, Analysis.user_id == current_user.id)
    )
    report = db.execute(statement).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report
