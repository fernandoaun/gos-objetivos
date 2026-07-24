"""Asegura tablas/columnas del módulo Objetivos (SQLite/Postgres sin migración formal)."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("objetivos", "responsable_texto", "VARCHAR(250)"),
    ("objetivos", "responsable_id", "INTEGER"),
    ("objetivos", "fecha_inicio", "DATE"),
    ("objetivos", "fecha_fin", "DATE"),
    ("objetivos", "estado", "VARCHAR(20) DEFAULT 'activo'"),
    ("objetivos", "origen", "VARCHAR(20) DEFAULT 'manual'"),
    ("objetivos", "orden", "INTEGER DEFAULT 0"),
    ("objetivos", "activo", "BOOLEAN DEFAULT TRUE"),
    ("kpi_indicadores", "numero", "INTEGER"),
    ("kpi_indicadores", "objetivo_codigo", "VARCHAR(20)"),
    ("kpi_indicadores", "responsable", "VARCHAR(250)"),
    ("kpi_indicadores", "medio", "VARCHAR(150)"),
    ("kpi_indicadores", "resultado_2025", "VARCHAR(80)"),
    ("kpi_indicadores", "meta_2026", "VARCHAR(80)"),
    ("kpi_indicadores", "meta_2026_num", "FLOAT"),
    ("kpi_indicadores", "valores_mes", "TEXT"),
    ("kpi_indicadores", "tipo_agregacion", "VARCHAR(20) DEFAULT 'promedio'"),
    ("kpi_indicadores", "observacion", "TEXT"),
    ("kpi_indicadores", "grupo", "VARCHAR(80)"),
    ("kpi_indicadores", "orden", "INTEGER DEFAULT 0"),
    ("kpi_indicadores", "activo", "BOOLEAN DEFAULT TRUE"),
    ("foda_items", "documento_id", "INTEGER"),
    ("foda_items", "area_id", "INTEGER"),
    ("foda_items", "responsable_id", "INTEGER"),
    ("foda_items", "fecha", "DATE"),
    ("foda_items", "orden", "INTEGER DEFAULT 0"),
    ("foda_items", "activo", "BOOLEAN DEFAULT TRUE"),
    ("foda_items", "origen", "VARCHAR(20) DEFAULT 'word'"),
]


def ensure_objetivos_schema() -> None:
    """Idempotente: crea tablas nuevas y agrega columnas faltantes."""
    from gos.modulos.objetivos.models import (  # noqa: F401
        Area,
        DafoTarea,
        FodaDocumento,
        FodaItem,
        KpiIndicador,
        Objetivo,
        PlaneamientoConfig,
        Responsable,
        Sector,
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
