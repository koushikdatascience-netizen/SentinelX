from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect,text
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


def test_intelligence_upgrade_preserves_preexisting_owner_and_workspace(tmp_path,monkeypatch):
    url=f"sqlite:///{(tmp_path/'existing.sqlite3').as_posix()}";monkeypatch.setenv("DATABASE_URL",url)
    cfg=Config(str(Path(__file__).resolve().parents[1]/"alembic.ini"));command.upgrade(cfg,"0011")
    engine=create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO users(id,email,password_hash,is_demo,created_at) VALUES ('existing-owner','owner@example.invalid','fixture',0,CURRENT_TIMESTAMP)"))
            connection.execute(text("INSERT INTO workspaces(id,owner_id,name,created_at) VALUES ('existing-workspace','existing-owner','Preserved business',CURRENT_TIMESTAMP)"))
        command.upgrade(cfg,"head")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT name FROM workspaces WHERE id='existing-workspace'"))=="Preserved business"
            assert {"research_jobs","business_facts","business_datasets"}.issubset(inspect(connection).get_table_names())
    finally:engine.dispose()
