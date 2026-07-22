"""Añade columnas nuevas en tablas de Vacaciones (SQLite/Postgres sin migración formal)."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("vacaciones", "comentario", "TEXT"),
    ("vacaciones", "nota_q", "TEXT"),
    ("vacaciones", "nota_r", "TEXT"),
]


def ensure_vacaciones_schema() -> None:
    """Idempotente: crea tablas nuevas y agrega columnas faltantes."""
    from gos.modulos.vacaciones.models import Registro, Vacacion  # noqa: F401

    db.create_all()
    inspector = inspect(db.engine)
    for table, column, coldef in _COLUMN_UPGRADES:
        if not inspector.has_table(table):
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column in existing:
            continue
        with db.engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}"))
