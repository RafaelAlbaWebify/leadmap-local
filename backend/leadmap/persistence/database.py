from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.leadmap.config import get_settings

from .base import Base


def build_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    if url.startswith("sqlite") and "///" in url:
        database_path = url.split("///", maxsplit=1)[1]
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def create_schema(target_engine: Engine = engine) -> None:
    Base.metadata.create_all(target_engine)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
