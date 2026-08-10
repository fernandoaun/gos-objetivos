"""Charlas de Buenas Prácticas Compartidas: acreditación libre fuera del wizard Programa→Plan."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    Acreditacion,
    AsistenciaEncuentro,
    CronogramaPuesto,
    Curso,
    EncuentroCapacitacion,
    Instructor,
    Participante,
    PlanCurso,
    ProgramaCapacitacion,
    ProgramaPlan,
    Puesto,
)
from gos.modulos.capacitacion.services.acreditacion_service import _upsert_registro

PROGRAMA_BPC_CODIGO = "BPC"
PROGRAMA_BPC_NOMBRE = "Buenas Prácticas Compartidas"
PLAN_BPC_NOMBRE = "Charlas"


def es_programa_bpc(programa: ProgramaCapacitacion | None) -> bool:
    if not programa:
        return False
    return (programa.codigo or "").strip().upper() == PROGRAMA_BPC_CODIGO


def asegurar_programa_bpc(empresa_id: int) -> tuple[ProgramaCapacitacion, ProgramaPlan]:
    """Programa/plan sistema para charlas; no se asigna a puestos (no genera requisitos)."""
    programa = ProgramaCapacitacion.query.filter_by(
        empresa_id=empresa_id, codigo=PROGRAMA_BPC_CODIGO, activo=True
    ).first()
    if not programa:
        programa = ProgramaCapacitacion(
            empresa_id=empresa_id,
            codigo=PROGRAMA_BPC_CODIGO,
            nombre=PROGRAMA_BPC_NOMBRE,
            tipo="interno",
            alcance="general",
            descripcion="Charlas y buenas prácticas compartidas (acreditación complementaria).",
            estado="programado",
            activo=True,
        )
        db.session.add(programa)
        db.session.flush()

    plan = (
        ProgramaPlan.query.filter_by(programa_id=programa.id, nombre=PLAN_BPC_NOMBRE).first()
        or programa.planes.order_by(ProgramaPlan.orden).first()
    )
    if not plan:
        plan = ProgramaPlan(programa_id=programa.id, nombre=PLAN_BPC_NOMBRE, orden=1)
        db.session.add(plan)
        db.session.flush()
    return programa, plan


def _slug_codigo(nombre: str) -> str:
    text = unicodedata.normalize("NFKD", nombre or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", "", text.upper())
    return (text[:16] or "CHARLA")


def _obtener_o_crear_curso_charla(empresa_id: int, nombre: str) -> Curso:
    nombre = nombre.strip()
    existente = (
        Curso.query.filter_by(empresa_id=empresa_id, activo=True, nombre=nombre)
        .order_by(Curso.id.desc())
        .first()
    )
    if existente:
        return existente

    base = f"BPC-{_slug_codigo(nombre)}"
    codigo = base[:30]
    n = 1
    while Curso.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        suffix = f"-{n}"
        codigo = f"{base[: 30 - len(suffix)]}{suffix}"
        n += 1

    curso = Curso(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        descripcion="Charla de Buenas Prácticas Compartidas",
        categoria=None,
        tipo=None,
        origen="interna",
        tipo_capacitacion=None,
        horas=None,
        modalidad=None,
        vigencia_meses=None,
        requiere_evaluacion=False,
        activo=True,
    )
    db.session.add(curso)
    db.session.flush()
    return curso


def _vincular_curso_al_plan(plan: ProgramaPlan, curso: Curso) -> None:
    if not PlanCurso.query.filter_by(plan_id=plan.id, curso_id=curso.id).first():
        orden = (plan.cursos.count() or 0) + 1
        db.session.add(PlanCurso(plan_id=plan.id, curso_id=curso.id, orden=orden))


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)
    if "T" in text:
        return datetime.fromisoformat(text.replace("Z", "")).date()
    return date.fromisoformat(text[:10])


def _parse_id_list(raw) -> list[int]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [int(x) for x in raw.split(",") if str(x).strip().isdigit()]
    result = []
    for x in raw:
        if x is None or x == "":
            continue
        result.append(int(x))
    return result


def _acreditar_charla(
    empresa_id: int,
    *,
    persona_id: int,
    programa_id: int,
    plan_id: int,
    curso_id: int,
    cronograma_persona_id: int | None,
    fecha_aprobacion: date,
    horas,
) -> Acreditacion:
    row = Acreditacion.query.filter_by(
        persona_id=persona_id,
        programa_id=programa_id,
        plan_id=plan_id,
        curso_id=curso_id,
    ).first()
    if not row:
        row = Acreditacion(
            empresa_id=empresa_id,
            persona_id=persona_id,
            programa_id=programa_id,
            plan_id=plan_id,
            curso_id=curso_id,
        )
        db.session.add(row)

    row.aprobo = True
    row.nota = None
    row.fecha_aprobacion = fecha_aprobacion
    row.fecha_vencimiento = None
    row.horas_acreditadas = horas
    row.cronograma_persona_id = cronograma_persona_id
    row.vigente = True
    return row


def crear_charla_buenas_practicas(empresa_id: int, data: dict) -> dict:
    """Registra una charla cerrada: personas, capacitador, nombre, fecha y evidencia opcional."""
    from gos.modulos.capacitacion.services.programa_service import _encuentro_dict

    nombre_curso = (data.get("nombre_curso") or data.get("titulo") or data.get("curso") or "").strip()
    if not nombre_curso:
        raise ValueError("Indicá el nombre del curso / charla")

    participante_ids = _parse_id_list(data.get("participante_ids"))
    if not participante_ids:
        raise ValueError("Seleccioná al menos una persona")

    fecha = _parse_date(data.get("fecha") or data.get("fecha_realizacion")) or date.today()

    instructor_id = data.get("instructor_id") or None
    instructor_nombre = (data.get("instructor") or data.get("capacitador") or "").strip() or None
    if instructor_id:
        inst = Instructor.query.filter_by(id=instructor_id, empresa_id=empresa_id, activo=True).first()
        if not inst:
            raise ValueError("Capacitador no válido")
        instructor_nombre = inst.nombre

    participantes_validos: list[Participante] = []
    for pid in participante_ids:
        p = Participante.query.filter_by(id=pid, empresa_id=empresa_id, activo=True).first()
        if p:
            participantes_validos.append(p)
    if not participantes_validos:
        raise ValueError("Ninguna persona seleccionada es válida")

    programa, plan = asegurar_programa_bpc(empresa_id)
    curso = _obtener_o_crear_curso_charla(empresa_id, nombre_curso)
    _vincular_curso_al_plan(plan, curso)

    puesto_ids = sorted({p.puesto_id for p in participantes_validos if p.puesto_id})
    titulo = f"BPC — {curso.nombre}"
    fecha_inicio_dt = datetime.combine(fecha, time(9, 0))

    encuentro = EncuentroCapacitacion(
        empresa_id=empresa_id,
        programa_id=programa.id,
        plan_id=plan.id,
        curso_id=curso.id,
        titulo=titulo,
        fecha=fecha,
        fecha_realizacion=fecha,
        fecha_inicio=fecha_inicio_dt,
        fecha_fin=fecha_inicio_dt,
        lugar=(data.get("lugar") or "").strip() or None,
        link_virtual=None,
        instructor=instructor_nombre,
        instructor_id=int(instructor_id) if instructor_id else None,
        origen="interna",
        estado="cerrado",
        observaciones=(data.get("observaciones") or "").strip() or None,
        es_buenas_practicas=True,
    )
    db.session.add(encuentro)
    db.session.flush()

    for pid in puesto_ids:
        if Puesto.query.filter_by(id=pid, empresa_id=empresa_id, activo=True).first():
            db.session.add(CronogramaPuesto(encuentro_id=encuentro.id, puesto_id=pid))

    for persona in participantes_validos:
        asist = AsistenciaEncuentro(
            encuentro_id=encuentro.id,
            participante_id=persona.id,
            asistencia="presente",
            aprobado=True,
            fecha_aprobacion=fecha,
            fecha_vencimiento=None,
        )
        db.session.add(asist)
        db.session.flush()
        _acreditar_charla(
            empresa_id,
            persona_id=persona.id,
            programa_id=programa.id,
            plan_id=plan.id,
            curso_id=curso.id,
            cronograma_persona_id=asist.id,
            fecha_aprobacion=fecha,
            horas=curso.horas,
        )
        _upsert_registro(empresa_id, encuentro, asist, curso)

    db.session.commit()
    data_out = _encuentro_dict(encuentro)
    data_out["es_buenas_practicas"] = True
    data_out["adjuntos"] = []
    return data_out


def listar_acreditaciones_bpc_persona(empresa_id: int, persona_id: int) -> list[dict]:
    """Charlas BPC ya acreditadas para la vista de matriz por persona."""
    programa = ProgramaCapacitacion.query.filter_by(
        empresa_id=empresa_id, codigo=PROGRAMA_BPC_CODIGO, activo=True
    ).first()
    if not programa:
        return []

    hoy = date.today()
    rows = (
        Acreditacion.query.filter_by(
            empresa_id=empresa_id,
            persona_id=persona_id,
            programa_id=programa.id,
            aprobo=True,
        )
        .order_by(Acreditacion.fecha_aprobacion.desc(), Acreditacion.id.desc())
        .all()
    )
    items = []
    for acr in rows:
        curso = acr.curso
        if not curso:
            continue
        vigente = bool(acr.vigente) and (
            acr.fecha_vencimiento is None or acr.fecha_vencimiento >= hoy
        )
        items.append(
            {
                "curso": curso.nombre,
                "hs": float(acr.horas_acreditadas or curso.horas or 0),
                "nota": float(acr.nota) if acr.nota is not None else None,
                "estado": "aprobada" if vigente else "pendiente",
                "empresa": "GOS Interno",
                "plan_nombre": acr.plan.nombre if acr.plan else PLAN_BPC_NOMBRE,
                "fecha_aprobacion": acr.fecha_aprobacion.isoformat() if acr.fecha_aprobacion else None,
            }
        )
    return items
