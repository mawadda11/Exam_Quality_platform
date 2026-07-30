from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Table, UniqueConstraint, create_engine, event, inspect, text
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
    "password_reset_tokens",
    "extraction_review_revisions",
    "findings",
    "reports",
    "supporting_materials",
    "supporting_material_annotations",
    "document_references",
    "reference_associations",
}


def _alembic_config(sqlite_url: str) -> Config:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sqlite_url)
    return cfg


@pytest.mark.parametrize(
    ("table", "column_name"),
    [
        (User.__table__, "email"),
        (Course.__table__, "code"),
    ],
)
def test_model_metadata_matches_migration_unique_constraints(
    table: Table, column_name: str
) -> None:
    assert any(
        isinstance(constraint, UniqueConstraint)
        and tuple(column.name for column in constraint.columns) == (column_name,)
        for constraint in table.constraints
    )
    assert not any(
        index.unique and tuple(column.name for column in index.columns) == (column_name,)
        for index in table.indexes
    )


def test_migration_upgrade_creates_expected_tables(tmp_path: Path) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'migration_upgrade.db'}"
    command.upgrade(_alembic_config(sqlite_url), "head")

    engine = create_engine(sqlite_url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert EXPECTED_TABLES <= tables
    assert "question_type_classifications" not in tables
    assert "question_type_review_revisions" not in tables


def test_final_migration_head_is_0012_and_no_0013_file_exists(tmp_path: Path) -> None:
    cfg = _alembic_config(f"sqlite:///{tmp_path / 'migration_head.db'}")

    assert ScriptDirectory.from_config(cfg).get_current_head() == "0012"
    assert list((BACKEND_ROOT / "alembic" / "versions").glob("0013*")) == []


def test_semantic_provenance_columns_and_duplicate_guard_are_migrated(
    tmp_path: Path,
) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'semantic_provenance.db'}"
    command.upgrade(_alembic_config(sqlite_url), "head")

    engine = create_engine(sqlite_url)
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("findings")}
    constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("findings")
    }
    engine.dispose()

    assert {
        "recommendation_id",
        "ai_provider",
        "ai_model",
        "prompt_template_version",
        "kb_version",
    } <= columns
    assert constraints["uq_findings_analysis_id_rule_id"] == (
        "analysis_id",
        "rule_id",
    )


def test_extraction_review_foundation_is_migrated(tmp_path: Path) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'extraction_review.db'}"
    command.upgrade(_alembic_config(sqlite_url), "head")

    engine = create_engine(sqlite_url)
    inspector = inspect(engine)
    analysis_columns = {column["name"] for column in inspector.get_columns("analyses")}
    finding_columns = {column["name"] for column in inspector.get_columns("findings")}
    revision_columns = {
        column["name"] for column in inspector.get_columns("extraction_review_revisions")
    }
    revision_constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("extraction_review_revisions")
    }
    analysis_constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("analyses")
    }
    analysis_foreign_keys = {
        foreign_key["name"]: (
            tuple(foreign_key["constrained_columns"]),
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in inspector.get_foreign_keys("analyses")
    }
    engine.dispose()

    assert "confirmed_review_id" in analysis_columns
    assert {"confidence_level", "evaluation_details"} <= finding_columns
    assert {
        "id",
        "analysis_id",
        "revision_number",
        "snapshot",
        "created_at",
    } <= revision_columns
    assert revision_constraints["uq_extraction_review_revisions_analysis_revision"] == (
        "analysis_id",
        "revision_number",
    )
    assert analysis_constraints["uq_analyses_confirmed_review_id"] == ("confirmed_review_id",)
    assert analysis_foreign_keys["fk_analyses_confirmed_review_id_extraction_review_revisions"] == (
        ("confirmed_review_id",),
        "extraction_review_revisions",
        ("id",),
    )


def test_faculty_authentication_foundation_is_migrated(tmp_path: Path) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'faculty_auth.db'}"
    command.upgrade(_alembic_config(sqlite_url), "head")

    engine = create_engine(sqlite_url)
    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    reset_columns = {column["name"] for column in inspector.get_columns("password_reset_tokens")}
    reset_constraints = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("password_reset_tokens")
    }
    engine.dispose()

    assert {
        "password_hash",
        "is_active",
        "email_verified",
        "token_version",
        "last_login_at",
    } <= user_columns
    assert {
        "id",
        "user_id",
        "token_hash",
        "expires_at",
        "used_at",
        "created_at",
    } <= reset_columns
    assert ("token_hash",) in reset_constraints


def test_batch3_language_and_retry_metadata_are_migrated(tmp_path: Path) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'batch3_metadata.db'}"
    command.upgrade(_alembic_config(sqlite_url), "head")

    engine = create_engine(sqlite_url)
    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    event_columns = {column["name"] for column in inspector.get_columns("processing_events")}
    report_columns = {column["name"] for column in inspector.get_columns("reports")}
    engine.dispose()

    assert "preferred_language" in user_columns
    assert {"failed_stage", "error_code", "retryable"} <= event_columns
    assert "language" in report_columns


def test_batch4_structured_evidence_and_version_columns_are_migrated(
    tmp_path: Path,
) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'batch4_structured.db'}"
    command.upgrade(_alembic_config(sqlite_url), "head")

    engine = create_engine(sqlite_url)
    inspector = inspect(engine)
    analysis_columns = {column["name"] for column in inspector.get_columns("analyses")}
    report_columns = {column["name"] for column in inspector.get_columns("reports")}
    association_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("reference_associations")
    }
    engine.dispose()

    assert "capability_version" in analysis_columns
    assert "capability_version" in report_columns
    assert "ck_reference_associations_one_target" in association_checks


def test_batch4_upgrade_preserves_historical_analysis_without_backfill(
    tmp_path: Path,
) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'batch4_historical.db'}"
    cfg = _alembic_config(sqlite_url)
    command.upgrade(cfg, "0011")

    engine = create_engine(sqlite_url)
    user_id = uuid.uuid4()
    course_id = uuid.uuid4()
    analysis_id = uuid.uuid4()
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, email, display_name, institution, department, user_type, password_hash, "
                "is_active, email_verified, token_version, last_login_at, preferred_language, "
                "created_at, updated_at) VALUES "
                "(:id, :email, :name, NULL, NULL, :user_type, NULL, 1, 0, 0, NULL, 'en', "
                ":created_at, :updated_at)"
            ),
            {
                "id": user_id.hex,
                "email": "batch4-legacy@example.test",
                "name": "Batch 4 Legacy",
                "user_type": "Faculty Member",
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO courses "
                "(id, code, name, department, program, created_at, updated_at) "
                "VALUES (:id, :code, :name, NULL, NULL, :created_at, :updated_at)"
            ),
            {
                "id": course_id.hex,
                "code": "B4-LEGACY",
                "name": "Historical Course",
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO analyses "
                "(id, user_id, course_id, exam_type, term, state, "
                "confirmed_review_id, predecessor_analysis_id, created_at, updated_at) "
                "VALUES (:id, :user_id, :course_id, :exam_type, :term, :state, "
                "NULL, NULL, :created_at, :updated_at)"
            ),
            {
                "id": analysis_id.hex,
                "user_id": user_id.hex,
                "course_id": course_id.hex,
                "exam_type": ExamType.MIDTERM.value,
                "term": "Historical",
                "state": "queued",
                "created_at": now,
                "updated_at": now,
            },
        )
    engine.dispose()

    command.upgrade(cfg, "head")
    engine = create_engine(sqlite_url)
    with engine.connect() as connection:
        capability_version = connection.execute(
            text("SELECT capability_version FROM analyses WHERE id = :id"),
            {"id": analysis_id.hex},
        ).scalar_one()
        structured_counts = [
            connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in (
                "supporting_materials",
                "supporting_material_annotations",
                "document_references",
                "reference_associations",
            )
        ]
    engine.dispose()

    assert capability_version is None
    assert structured_counts == [0, 0, 0, 0]


def test_batch4_revision_downgrade_returns_to_current_predecessor(
    tmp_path: Path,
) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'batch4_downgrade.db'}"
    cfg = _alembic_config(sqlite_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0011")

    engine = create_engine(sqlite_url)
    inspector = inspect(engine)
    assert "capability_version" not in {
        column["name"] for column in inspector.get_columns("analyses")
    }
    assert not {
        "supporting_materials",
        "supporting_material_annotations",
        "document_references",
        "reference_associations",
    } & set(inspector.get_table_names())
    engine.dispose()


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


def test_auth_migration_preserves_existing_version1_user(tmp_path: Path) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'v1_to_v2_auth.db'}"
    cfg = _alembic_config(sqlite_url)
    command.upgrade(cfg, "0008")

    engine = create_engine(sqlite_url)
    user_id = uuid.uuid4()
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, email, display_name, institution, department, user_type, "
                "created_at, updated_at) "
                "VALUES (:id, :email, :name, NULL, NULL, :user_type, :created_at, :updated_at)"
            ),
            {
                "id": user_id.hex,
                "email": "legacy@university.edu",
                "name": "Legacy Faculty",
                "user_type": "Faculty Member",
                "created_at": now,
                "updated_at": now,
            },
        )
    engine.dispose()

    command.upgrade(cfg, "head")
    engine = create_engine(sqlite_url)
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT password_hash, is_active, email_verified, token_version "
                "FROM users WHERE email = :email"
            ),
            {"email": "legacy@university.edu"},
        ).one()
    engine.dispose()

    assert row.password_hash is None
    assert row.is_active in (True, 1)
    assert row.email_verified in (False, 0)
    assert row.token_version == 0
