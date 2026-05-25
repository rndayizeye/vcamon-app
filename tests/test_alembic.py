from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

EXPECTED_TABLES = {
    "alembic_version",
    "arrow_links",
    "case_partner_relationships",
    "cases",
    "ghostings",
    "lab_results",
    "map_entries",
    "partners",
    "relationship_reports",
    "symptom_entries",
    "timeline_events",
}


def test_alembic_upgrade_creates_expected_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "alembic_test.db"
    database_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    repo_root = Path(__file__).resolve().parents[1]
    config = Config(str(repo_root / "fastapi_app" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repo_root / "fastapi_app" / "migrations")
    )

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))
