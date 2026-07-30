from __future__ import annotations

import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.config import Settings
from app.core.identity import IdentityError, resolve_faculty_user
from app.db.base import Base
from app.db.session import create_engine_from_url
from app.models.user import User
from app.services.auth.tokens import AccessTokenClaims


@pytest.fixture()
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'identity_test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _claims(email: str = "alice@kau.edu.sa") -> AccessTokenClaims:
    return AccessTokenClaims(
        user_id=uuid.uuid5(uuid.NAMESPACE_URL, email),
        email=email,
        display_name="Alice",
        token_version=0,
    )


def test_test_environment_can_provision_signed_fixture_identity(db_session: Session) -> None:
    user = resolve_faculty_user(
        db_session,
        _claims(),
        Settings(app_env="test", secret_key="test-secret-key-not-for-production"),
    )
    assert user.email == "alice@kau.edu.sa"
    assert user.is_active is True


def test_non_test_environment_never_provisions_missing_user(db_session: Session) -> None:
    with pytest.raises(IdentityError, match="unavailable"):
        resolve_faculty_user(
            db_session,
            _claims(),
            Settings(app_env="development", secret_key="development-secret-key-value"),
        )


def test_revoked_token_version_is_rejected(db_session: Session) -> None:
    claims = _claims("revoked@kau.edu.sa")
    user = User(
        id=claims.user_id,
        email=claims.email,
        display_name="Revoked",
        token_version=1,
        password_hash=None,
    )
    db_session.add(user)
    db_session.flush()

    with pytest.raises(IdentityError, match="revoked"):
        resolve_faculty_user(
            db_session,
            claims,
            Settings(app_env="test", secret_key="test-secret-key-not-for-production"),
        )
