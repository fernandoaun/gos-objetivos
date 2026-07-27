"""Asegura tablas/columnas del módulo O&M."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("om_module_personnel", "participante_id", "INTEGER"),
    ("om_module_items", "unidad_id", "INTEGER"),
]


def ensure_om_schema() -> None:
    from gos.modulos.om.models import (  # noqa: F401
        OmAuditLog,
        OmItem,
        OmModule,
        OmPersonnel,
        OmPhone,
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
