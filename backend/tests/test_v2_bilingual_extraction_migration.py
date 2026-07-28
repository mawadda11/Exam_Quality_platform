from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_bilingual_extraction_metadata_columns_are_migrated(tmp_path: Path) -> None:
    sqlite_url = f"sqlite:///{tmp_path / 'bilingual_extraction.db'}"
    config = Config(str(_BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", sqlite_url)

    command.upgrade(config, "head")

    engine = create_engine(sqlite_url)
    columns = {column["name"] for column in inspect(engine).get_columns("uploaded_files")}
    engine.dispose()

    assert {
        "detected_language",
        "extraction_method",
        "extraction_confidence",
        "review_recommended",
        "parser_layout",
    } <= columns
