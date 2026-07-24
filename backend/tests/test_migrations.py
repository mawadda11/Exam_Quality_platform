from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.core.domain import ExamType, UploadedFileType
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.uploaded_file import UploadedFile
from app.models.user import User

BACKEND_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "users",
    "courses",
    "analyses",
    "uploaded_files",
    "processing_events",
    "findings",
    "reports",
}


def _alembic_config(sqlite_url: str) -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sqlite_url)
    return cfg


def test_migration_upgrade_creates_expected_tables(tmp_path: Path) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'migration_upgrade.db'}"
    command.upgrade(_alembic_config(sqlite_url), "head")

    engine = create_engine(sqlite_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert EXPECTED_TABLES <= tables


def test_migration_enforces_dual_file_unique_constraint(tmp_path: Path) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'migration_constraint.db'}"
    command.upgrade(_alembic_config(sqlite_url), "head")

    engine = create_engine(sqlite_url)
    with Session(engine) as session:
        user = User(email="migtest@kau.edu.sa", display_name="Mig Test")
        course = Course(code="MIG-100", name="Migration Test Course")
        session.add_all([user, course])
        session.flush()

        analysis = Analysis(
            user_id=user.id, course_id=course.id, exam_type=ExamType.MIDTERM, term="Test"
        )
        session.add(analysis)
        session.flush()

        session.add(
            UploadedFile(
                analysis_id=analysis.id,
                file_type=UploadedFileType.EXAM,
                original_filename="a.pdf",
                storage_key="k1",
                mime_type="application/pdf",
                size_bytes=10,
                sha256_hash="a" * 64,
            )
        )
        session.commit()

        session.add(
            UploadedFile(
                analysis_id=analysis.id,
                file_type=UploadedFileType.EXAM,
                original_filename="b.pdf",
                storage_key="k2",
                mime_type="application/pdf",
                size_bytes=10,
                sha256_hash="b" * 64,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    engine.dispose()


def test_predecessor_analysis_id_restricts_deletion_of_a_referenced_predecessor(
    tmp_path: Path,
) -> None:
    # M10 decision 6: RESTRICT for predecessor relationships. SQLite ignores
    # foreign-key actions unless explicitly enabled per-connection - without
    # this, the DELETE below would silently succeed and this test would
    # prove nothing about the migration's actual ondelete="RESTRICT".
    sqlite_url = f"sqlite:///{tmp_path / 'migration_restrict.db'}"
    command.upgrade(_alembic_config(sqlite_url), "head")

    engine = create_engine(sqlite_url)
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))

    with Session(engine) as session:
        user = User(email="restrict@kau.edu.sa", display_name="Restrict Test")
        course = Course(code="RST-100", name="Restrict Test Course")
        session.add_all([user, course])
        session.flush()

        predecessor = Analysis(
            user_id=user.id, course_id=course.id, exam_type=ExamType.MIDTERM, term="Test"
        )
        session.add(predecessor)
        session.flush()

        reanalysis = Analysis(
            user_id=user.id,
            course_id=course.id,
            exam_type=ExamType.MIDTERM,
            term="Test",
            predecessor_analysis_id=predecessor.id,
        )
        session.add(reanalysis)
        session.commit()

        session.delete(predecessor)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    engine.dispose()


def test_migration_downgrade_removes_all_tables(tmp_path: Path) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'migration_downgrade.db'}"
    cfg = _alembic_config(sqlite_url)

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    engine = create_engine(sqlite_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert not (EXPECTED_TABLES & tables)
