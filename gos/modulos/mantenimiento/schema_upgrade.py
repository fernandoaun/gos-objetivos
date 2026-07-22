"""Asegura tablas/columnas del módulo Mantenimiento."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("mant_vtv", "bloqueado", "BOOLEAN DEFAULT 0"),
    ("mant_vtv", "resultado_ultimo", "VARCHAR(32)"),
    ("mant_vtv", "observaciones", "TEXT"),
]


def ensure_mantenimiento_schema() -> None:
    from gos.modulos.mantenimiento.models import (  # noqa: F401
        MantPlanCelda,
        MantPlanMeta,
        MantUnidad,
        MantVtv,
        MantVtvTurno,
    )

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
