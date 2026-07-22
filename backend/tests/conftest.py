from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  ensure all tables are registered on Base.metadata
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import create_engine_from_url, get_db
from app.main import app


@pytest.fixture()
def upload_root(tmp_path: Path) -> Path:
    root = tmp_path / "uploads"
    root.mkdir()
    return root


@pytest.fixture()
def test_settings(upload_root: Path) -> Settings:
    return Settings(
        secret_key="test-secret-key-not-for-production",
        database_url="sqlite:///:memory:",
        upload_root=str(upload_root),
        max_upload_mb=1,
    )


@pytest.fixture()
def db_engine(tmp_path: Path) -> Generator[Engine, None, None]:
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(test_settings: Settings, db_engine: Engine) -> Generator[TestClient, None, None]:
    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
