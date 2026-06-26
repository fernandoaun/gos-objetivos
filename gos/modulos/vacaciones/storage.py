from __future__ import annotations

import sqlite3

from gos.extensions import db
from gos.modulos.vacaciones.database import DB_PATH, LEGACY_DB
from gos.modulos.vacaciones.models import Registro, Vacacion


def migrate_legacy_data_if_empty() -> None:
    """Copia datos del SQLite local o legacy si las tablas en PostgreSQL están vacías."""
    from flask import current_app

    if current_app.config.get("TESTING"):
        return
    if Registro.query.limit(1).first() is not None:
        return
    if _migrate_from_local_sqlite(DB_PATH):
        return
    _migrate_from_local_sqlite(LEGACY_DB)


def _migrate_from_local_sqlite(path) -> bool:
    from pathlib import Path

    p = Path(path)
    if not p.is_file() or p.stat().st_size == 0:
        return False
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    try:
        reg_rows = conn.execute("SELECT * FROM registros").fetchall()
        vac_rows = conn.execute("SELECT * FROM vacaciones").fetchall()
        if not reg_rows and not vac_rows:
            return False
        for row in reg_rows:
            data = dict(row)
            data.pop("id", None)
            db.session.add(Registro(**data))
        for row in vac_rows:
            data = dict(row)
            data.pop("id", None)
            db.session.add(Vacacion(**data))
        db.session.commit()
        return True
    except sqlite3.Error:
        db.session.rollback()
        return False
    finally:
        conn.close()


def reset_for_tests() -> None:
    """Limpia tablas de vacaciones (solo tests)."""
    Vacacion.query.delete()
    Registro.query.delete()
    db.session.commit()
