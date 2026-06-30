"""Añade columnas nuevas en tablas existentes (SQLite/Postgres sin migración formal)."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("cap_participantes", "apellido", "VARCHAR(150)"),
    ("cap_participantes", "dni", "VARCHAR(20)"),
    ("cap_participantes", "telefono", "VARCHAR(40)"),
    ("cap_participantes", "fecha_ingreso", "DATE"),
    ("cap_participantes", "observaciones", "TEXT"),
    ("cap_participantes", "foto_path", "VARCHAR(500)"),
    ("cap_cursos", "tipo_capacitacion", "VARCHAR(30)"),
    ("cap_cursos", "categoria", "VARCHAR(30)"),
    ("cap_cursos", "tipo", "VARCHAR(30)"),
    ("cap_cursos", "origen", "VARCHAR(30)"),
    ("cap_cursos", "requiere_evaluacion", "BOOLEAN DEFAULT FALSE"),
    ("cap_cursos", "puntaje_minimo", "NUMERIC(5,2)"),
    ("cap_cursos", "instructor_id", "INTEGER"),
    ("cap_encuentros", "link_virtual", "VARCHAR(500)"),
    ("cap_programas", "puesto_id", "INTEGER"),
    ("cap_programas", "alcance", "VARCHAR(20) DEFAULT 'general'"),
    ("cap_config", "pct_cumplimiento_minimo", "INTEGER DEFAULT 80"),
    ("cap_config", "notif_email_activo", "BOOLEAN DEFAULT FALSE"),
    ("cap_config", "notif_vencimiento", "BOOLEAN DEFAULT TRUE"),
    ("cap_config", "notif_obligatorio", "BOOLEAN DEFAULT TRUE"),
    ("cap_config", "notif_curso_proximo", "BOOLEAN DEFAULT TRUE"),
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
        TaxonomiaItem,
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
    _migrar_clasificacion_cursos()


def _migrar_clasificacion_cursos() -> None:
    from gos.modulos.capacitacion.models import Curso
    from gos.modulos.capacitacion.services.taxonomia_service import (
        clasificacion_desde_legacy,
        tipo_capacitacion_legacy,
    )

    cambios = False
    for curso in Curso.query.filter(Curso.categoria.is_(None)).all():
        cat, tipo, origen = clasificacion_desde_legacy(curso.empresa_id, curso.tipo_capacitacion)
        if not cat and not curso.tipo_capacitacion:
            continue
        if cat:
            curso.categoria = cat
            curso.tipo = tipo
            curso.origen = origen
            curso.tipo_capacitacion = tipo_capacitacion_legacy(cat, tipo)
            cambios = True
    if cambios:
        db.session.commit()
