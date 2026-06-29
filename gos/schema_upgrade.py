"""Añade columnas nuevas en tablas del núcleo (SQLite/Postgres sin migración formal)."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("usuarios", "perfil_id", "INTEGER"),
]


def ensure_core_schema() -> None:
    from gos.models import Empresa, Perfil, Usuario  # noqa: F401

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
