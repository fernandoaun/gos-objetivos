"""Añade columnas nuevas en tablas existentes (SQLite/Postgres sin migración formal)."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("cap_participantes", "apellido", "VARCHAR(150)"),
    ("cap_participantes", "dni", "VARCHAR(20)"),
    ("cap_participantes", "telefono", "VARCHAR(40)"),
    ("cap_participantes", "centro", "VARCHAR(150)"),
    ("cap_participantes", "centro_id", "INTEGER"),
    ("cap_participantes", "fecha_ingreso", "DATE"),
    ("cap_participantes", "observaciones", "TEXT"),
    ("cap_participantes", "foto_path", "VARCHAR(500)"),
    ("cap_cursos", "tipo_capacitacion", "VARCHAR(30)"),
    ("cap_cursos", "categoria", "VARCHAR(30)"),
    ("cap_cursos", "tipo", "VARCHAR(30)"),
    ("cap_cursos", "origen", "VARCHAR(30)"),
    ("cap_cursos", "temas", "TEXT"),
    ("cap_cursos", "requiere_evaluacion", "BOOLEAN DEFAULT FALSE"),
    ("cap_cursos", "puntaje_minimo", "NUMERIC(5,2)"),
    ("cap_cursos", "instructor_id", "INTEGER"),
    ("cap_encuentros", "link_virtual", "VARCHAR(500)"),
    ("cap_encuentros", "origen", "VARCHAR(30)"),
    ("cap_encuentros", "empresa_capacitadora_id", "INTEGER"),
    ("cap_encuentros", "instructor_id", "INTEGER"),
    ("cap_encuentros", "plan_id", "INTEGER"),
    ("cap_encuentros", "fecha_inicio", "TIMESTAMP"),
    ("cap_encuentros", "fecha_fin", "TIMESTAMP"),
    ("cap_encuentros", "material_adjunto_url", "VARCHAR(500)"),
    ("cap_encuentros", "resultados_adjunto_url", "VARCHAR(500)"),
    ("cap_asistencias", "fecha_aprobacion", "DATE"),
    ("cap_asistencias", "fecha_vencimiento", "DATE"),
    ("cap_programas", "puesto_id", "INTEGER"),
    ("cap_programas", "alcance", "VARCHAR(20) DEFAULT 'general'"),
    ("cap_programas", "tipo", "VARCHAR(20) DEFAULT 'interno'"),
    ("cap_programas", "empresa_capacitadora_id", "INTEGER"),
    ("cap_config", "pct_cumplimiento_minimo", "INTEGER DEFAULT 80"),
    ("cap_config", "notif_email_activo", "BOOLEAN DEFAULT FALSE"),
    ("cap_config", "notif_vencimiento", "BOOLEAN DEFAULT TRUE"),
    ("cap_config", "notif_obligatorio", "BOOLEAN DEFAULT TRUE"),
    ("cap_config", "notif_curso_proximo", "BOOLEAN DEFAULT TRUE"),
    ("cap_config", "emails_destinatarios", "TEXT"),
    ("cap_config", "emails_por_sector", "TEXT"),
    ("cap_config", "emails_por_rol", "TEXT"),
    ("cap_config", "ultimo_envio_notif", "TIMESTAMP"),
    ("cap_puestos", "sector_id", "INTEGER"),
]


def ensure_capacitacion_schema() -> None:
    """Idempotente: crea tablas nuevas y agrega columnas faltantes."""
    from gos.modulos.capacitacion.models import (  # noqa: F401
        Acreditacion,
        AlertaCapacitacion,
        CapacitacionConfig,
        Centro,
        CronogramaPuesto,
        EmpresaCapacitadora,
        Instructor,
        PlanCurso,
        ProgramaPlan,
        ProgramaPuesto,
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
    _migrar_estructura_programas()
    _migrar_sector_puesto()
    _migrar_centros_texto()


def _migrar_centros_texto() -> None:
    """Convierte el campo texto centro en referencias al catálogo cap_centros."""
    from gos.modulos.capacitacion.models import Centro, Participante
    from gos.modulos.capacitacion.services.catalogo_service import centro_id_desde_texto

    inspector = inspect(db.engine)
    if not inspector.has_table("cap_participantes"):
        return
    cols = {c["name"] for c in inspector.get_columns("cap_participantes")}
    if "centro" not in cols or "centro_id" not in cols:
        return

    cambios = False
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, empresa_id, centro FROM cap_participantes "
                "WHERE centro IS NOT NULL AND centro_id IS NULL"
            )
        ).fetchall()

    for row_id, empresa_id, centro_text in rows:
        nombre = (centro_text or "").strip()
        if not nombre:
            continue
        participante = Participante.query.get(row_id)
        if not participante or participante.centro_id:
            continue
        centro_id = centro_id_desde_texto(empresa_id, centro_text)
        if centro_id:
            participante.centro_id = centro_id
            cambios = True

    if cambios:
        db.session.commit()


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


def _migrar_estructura_programas() -> None:
    """Convierte programas legados (puesto + requisitos) a Programa→Plan→Cursos."""
    from gos.modulos.capacitacion.models import (
        PlanCurso,
        ProgramaCapacitacion,
        ProgramaPlan,
        ProgramaPuesto,
        RequisitoFormacion,
    )

    cambios = False
    for programa in ProgramaCapacitacion.query.filter_by(activo=True).all():
        if not programa.tipo:
            programa.tipo = "interno"
            cambios = True

        puestos_ids = {pp.puesto_id for pp in programa.puestos_asignados.all()}
        if programa.puesto_id and programa.puesto_id not in puestos_ids:
            db.session.add(ProgramaPuesto(programa_id=programa.id, puesto_id=programa.puesto_id))
            puestos_ids.add(programa.puesto_id)
            cambios = True

        if not puestos_ids:
            continue

        plan = programa.planes.order_by(ProgramaPlan.orden).first()
        if not plan:
            plan = ProgramaPlan(programa_id=programa.id, nombre="General", orden=1)
            db.session.add(plan)
            db.session.flush()
            cambios = True

        cursos_en_plan = {pc.curso_id for pc in plan.cursos.all()}
        requisitos = RequisitoFormacion.query.filter(
            RequisitoFormacion.empresa_id == programa.empresa_id,
            RequisitoFormacion.puesto_id.in_(puestos_ids),
            RequisitoFormacion.curso_id.isnot(None),
        ).all()
        orden = len(cursos_en_plan)
        for req in requisitos:
            if req.curso_id in cursos_en_plan:
                continue
            orden += 1
            db.session.add(PlanCurso(plan_id=plan.id, curso_id=req.curso_id, orden=orden))
            cursos_en_plan.add(req.curso_id)
            cambios = True

    if cambios:
        db.session.commit()


def _migrar_sector_puesto() -> None:
    """Backfill sector_id en puestos desde el sector más frecuente de sus participantes."""
    from collections import Counter

    from gos.modulos.capacitacion.models import Participante, Puesto

    cambios = False
    for puesto in Puesto.query.filter(Puesto.sector_id.is_(None)).all():
        sectores = [
            p.sector_id
            for p in Participante.query.filter_by(puesto_id=puesto.id, activo=True).all()
            if p.sector_id
        ]
        if not sectores:
            continue
        puesto.sector_id = Counter(sectores).most_common(1)[0][0]
        cambios = True
    if cambios:
        db.session.commit()
