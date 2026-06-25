"""Añade columnas nuevas en tablas existentes (SQLite/Postgres sin migración formal)."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("cap_participantes", "apellido", "VARCHAR(150)"),
    ("cap_participantes", "dni", "VARCHAR(20)"),
    ("cap_participantes", "telefono", "VARCHAR(40)"),
    ("cap_participantes", "fecha_ingreso", "DATE"),
    ("cap_participantes", "observaciones", "TEXT"),
    ("cap_cursos", "tipo_capacitacion", "VARCHAR(30)"),
    ("cap_cursos", "requiere_evaluacion", "BOOLEAN DEFAULT 0"),
    ("cap_cursos", "puntaje_minimo", "NUMERIC(5,2)"),
    ("cap_cursos", "instructor_id", "INTEGER"),
    ("cap_encuentros", "link_virtual", "VARCHAR(500)"),
    ("cap_config", "pct_cumplimiento_minimo", "INTEGER DEFAULT 80"),
    ("cap_config", "notif_email_activo", "BOOLEAN DEFAULT 0"),
    ("cap_config", "notif_vencimiento", "BOOLEAN DEFAULT 1"),
    ("cap_config", "notif_obligatorio", "BOOLEAN DEFAULT 1"),
    ("cap_config", "notif_curso_proximo", "BOOLEAN DEFAULT 1"),
    ("cap_config", "emails_destinatarios", "TEXT"),
    ("cap_config", "emails_por_sector", "TEXT"),
    ("cap_config", "emails_por_rol", "TEXT"),
    ("cap_config", "ultimo_envio_notif", "DATETIME"),
]


def ensure_capacitacion_schema() -> None:
    """Idempotente: crea tablas nuevas y agrega columnas faltantes."""
    from gos.modulos.capacitacion.models import (  # noqa: F401
        AlertaCapacitacion,
        CapacitacionConfig,
        Instructor,
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
