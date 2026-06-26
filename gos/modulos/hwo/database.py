from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

from gos import env

DATA_DIR = env.hwo_data_dir()
DB_PATH = env.hwo_db_path()

_engine = None
SessionLocal: scoped_session | None = None


class Base(DeclarativeBase):
    pass


def _db_url() -> str:
    return f"sqlite:///{DB_PATH.resolve()}"


def get_engine():
    global _engine, SessionLocal
    if _engine is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(_db_url(), connect_args={"check_same_thread": False})
        SessionLocal = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        )
    return _engine


def get_session():
    get_engine()
    return SessionLocal()


def init_db() -> None:
    from gos.modulos.hwo.models import HwoDataset, HwoModalidad  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_hwo_dataset_saved ON hwo_datasets(saved_at)"))
        conn.commit()


def reset_for_tests() -> None:
    """Reinicia el motor SQLite (solo tests)."""
    global _engine, SessionLocal
    if SessionLocal is not None:
        SessionLocal.remove()
    if _engine is not None:
        _engine.dispose()
    _engine = None
    SessionLocal = None
    if DB_PATH.is_file():
        DB_PATH.unlink()
