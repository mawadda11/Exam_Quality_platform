"""Local-development identity adapter.

NOT for production use. Trusts a client-supplied header instead of verifying
credentials. Replace with a real authentication mechanism before any
non-development deployment.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.domain import UserType
from app.models.user import User


def get_or_create_faculty_user(
    db: Session,
    email: str,
    display_name: str | None = None,
    institution: str | None = None,
    department: str | None = None,
) -> User:
    normalized_email = email.strip().lower()
    existing = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
    if existing is not None:
        return existing

    user = User(
        email=normalized_email,
        display_name=(display_name or normalized_email).strip(),
        institution=institution,
        department=department,
        user_type=UserType.FACULTY_MEMBER,
    )
    db.add(user)
    db.flush()
    return user
