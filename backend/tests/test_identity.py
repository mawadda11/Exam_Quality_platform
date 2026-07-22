from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.domain import UserType
from app.core.identity import get_or_create_faculty_user
from app.db.base import Base
from app.db.session import create_engine_from_url


@pytest.fixture()
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    # File-based, not ":memory:" - an in-memory SQLite DB is per-connection, and a
    # commit() below can release the connection back to the pool, so a *second*
    # checkout would silently see an empty database without a real file backing it.
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'identity_test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_get_or_create_creates_new_user(db_session: Session) -> None:
    user = get_or_create_faculty_user(
        db_session, email="Prof.Alice@KAU.EDU.SA", display_name="Alice"
    )
    assert user.email == "prof.alice@kau.edu.sa"
    assert user.user_type == UserType.FACULTY_MEMBER


def test_get_or_create_returns_same_user_on_second_call(db_session: Session) -> None:
    first = get_or_create_faculty_user(db_session, email="bob@kau.edu.sa", display_name="Bob")
    db_session.commit()

    second = get_or_create_faculty_user(
        db_session, email="Bob@KAU.EDU.SA", display_name="Someone Else"
    )

    assert first.id == second.id
    assert second.display_name == "Bob"
