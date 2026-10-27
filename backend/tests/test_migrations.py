from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect
from app.workspace_store import Base


def test_fresh_database_upgrade_matches_models_and_is_repeatable(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migration-test.sqlite3').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert "evidence_quotas" in inspect(connection).get_table_names()
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    finally:
        engine.dispose()
