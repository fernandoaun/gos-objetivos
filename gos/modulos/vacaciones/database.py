from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

from gos import env
from gos.config import BASE_DIR

DATA_DIR = env.vacaciones_db_path().parent
DB_PATH = env.vacaciones_db_path()
LEGACY_DB = BASE_DIR.parent / "LUZ GALLARDO" / "indicadores-app" / "data" / "indicadores.db"

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
    from gos.modulos.vacaciones.models import Registro, Vacacion  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reg_fecha ON registros(fecha)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reg_empleado ON registros(empleado)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reg_sector ON registros(sector)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reg_situacion ON registros(situacion)"))
        conn.commit()


def migrate_legacy_data_if_empty() -> None:
    """Copia la base del proyecto Luz Gallardo si el módulo está vacío."""
    init_db()
    if not LEGACY_DB.is_file():
        return
    if DB_PATH.is_file() and DB_PATH.stat().st_size > 0:
        session = get_session()
        try:
            from gos.modulos.vacaciones.models import Registro

            if session.query(Registro).limit(1).first() is not None:
                return
        finally:
            session.close()
    shutil.copy2(LEGACY_DB, DB_PATH)


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
