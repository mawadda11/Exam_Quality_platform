from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.identity import get_or_create_faculty_user
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.report import Report
from app.models.user import User


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    x_dev_user_email: Annotated[str | None, Header()] = None,
    x_dev_user_name: Annotated[str | None, Header()] = None,
    x_dev_user_institution: Annotated[str | None, Header()] = None,
    x_dev_user_department: Annotated[str | None, Header()] = None,
) -> User:
    if not x_dev_user_email or "@" not in x_dev_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-Dev-User-Email header.",
        )

    return get_or_create_faculty_user(
        db,
        email=x_dev_user_email,
        display_name=x_dev_user_name,
        institution=x_dev_user_institution,
        department=x_dev_user_department,
    )


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
        # Same IDOR-safe non-disclosure as get_owned_analysis.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report
