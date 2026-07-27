"""Asegura tablas/columnas del módulo Mantenimiento."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("mant_vtv", "bloqueado", "BOOLEAN DEFAULT FALSE"),
    ("mant_vtv", "resultado_ultimo", "VARCHAR(32)"),
    ("mant_vtv", "observaciones", "TEXT"),
    ("mant_reporte_ordenes", "nro_solicitud", "VARCHAR(64)"),
    ("mant_reporte_ordenes", "estado_solicitud", "VARCHAR(64)"),
    ("mant_reporte_ordenes", "ingreso_taller", "DATE"),
    ("mant_reporte_ordenes", "km", "FLOAT"),
    ("mant_reporte_ordenes", "hs", "FLOAT"),
    ("mant_reporte_tareas", "nro_tarea", "VARCHAR(64)"),
    ("mant_reporte_tareas", "estado", "VARCHAR(64)"),
    ("mant_reporte_tareas", "solicitante", "VARCHAR(128)"),
    ("mant_reporte_tareas", "urgencia", "VARCHAR(64)"),
    ("mant_reporte_tareas", "descripcion", "VARCHAR(500)"),
    ("mant_reporte_tareas", "cant_personal", "FLOAT"),
    ("mant_reporte_tareas", "tercerizado", "VARCHAR(64)"),
]

_INDEX_UPGRADES = [
    ("uq_mant_reporte_orden_nro", "mant_reporte_ordenes", "nro_orden", True),
    ("uq_mant_reporte_tarea_nro", "mant_reporte_tareas", "nro_tarea", True),
    ("uq_mant_reporte_solicitud_nro", "mant_reporte_solicitudes", "nro_solicitud", True),
    ("ix_mant_reporte_solicitud_anio_mes", "mant_reporte_solicitudes", "anio, mes", False),
]


def ensure_mantenimiento_schema() -> None:
    from gos.modulos.mantenimiento.models import (  # noqa: F401
        MantPlanCelda,
        MantPlanMeta,
        MantReporteOrden,
        MantReporteSolicitud,
        MantReporteTarea,
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

    inspector = inspect(db.engine)
    for name, table, columns, unique in _INDEX_UPGRADES:
        if not inspector.has_table(table):
            continue
        existing_indexes = {ix["name"] for ix in inspector.get_indexes(table)}
        # UniqueConstraint también aparece en get_unique_constraints
        existing_uniques = {
            uc.get("name") for uc in inspector.get_unique_constraints(table) if uc.get("name")
        }
        if name in existing_indexes or name in existing_uniques:
            continue
        kind = "UNIQUE INDEX" if unique else "INDEX"
        with db.engine.begin() as conn:
            try:
                conn.execute(text(f"CREATE {kind} IF NOT EXISTS {name} ON {table} ({columns})"))
            except Exception:
                # SQLite/Postgres: si hay duplicados históricos, no bloquear el arranque.
                pass
