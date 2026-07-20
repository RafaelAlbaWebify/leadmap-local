from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from backend.leadmap.persistence.database import build_engine


def test_alembic_upgrade_creates_versioned_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "leadmap-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    inspector = inspect(build_engine(database_url))
    tables = set(inspector.get_table_names())

    assert "alembic_version" in tables
    assert {
        "territories",
        "query_templates",
        "businesses",
        "business_locations",
        "search_runs",
        "observations",
    }.issubset(tables)
