"""CRUD de acreditaciones (además del flujo automático en cierre de cronograma)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    Acreditacion,
    Curso,
    Participante,
    ProgramaCapacitacion,
    ProgramaPlan,
)
from gos.modulos.capacitacion.services.acreditacion_service import (
    calcular_aprobacion,
    calcular_fecha_vencimiento,
    refrescar_vigencias,
)


def _acr_dict(acr: Acreditacion) -> dict:
    return {
        "id": acr.id,
        "persona_id": acr.persona_id,
        "persona_nombre": acr.persona.nombre_completo if acr.persona else None,
        "programa_id": acr.programa_id,
        "programa_nombre": acr.programa.nombre if acr.programa else None,
        "plan_id": acr.plan_id,
        "plan_nombre": acr.plan.nombre if acr.plan else None,
        "curso_id": acr.curso_id,
        "curso_nombre": acr.curso.nombre if acr.curso else None,
        "aprobo": acr.aprobo,
        "nota": float(acr.nota) if acr.nota is not None else None,
        "horas_acreditadas": float(acr.horas_acreditadas) if acr.horas_acreditadas is not None else None,
        "fecha_aprobacion": acr.fecha_aprobacion.isoformat() if acr.fecha_aprobacion else None,
        "fecha_vencimiento": acr.fecha_vencimiento.isoformat() if acr.fecha_vencimiento else None,
        "vigente": acr.vigente,
        "cronograma_persona_id": acr.cronograma_persona_id,
    }


def listar_acreditaciones(
    empresa_id: int,
    *,
    persona_id: int | None = None,
    programa_id: int | None = None,
    plan_id: int | None = None,
    curso_id: int | None = None,
) -> list[dict]:
    refrescar_vigencias(empresa_id)
    q = Acreditacion.query.filter_by(empresa_id=empresa_id)
    if persona_id:
        q = q.filter_by(persona_id=persona_id)
    if programa_id:
        q = q.filter_by(programa_id=programa_id)
    if plan_id:
        q = q.filter_by(plan_id=plan_id)
    if curso_id:
        q = q.filter_by(curso_id=curso_id)
    return [_acr_dict(a) for a in q.order_by(Acreditacion.id.desc()).all()]


def obtener_acreditacion(empresa_id: int, acreditacion_id: int) -> dict:
    acr = Acreditacion.query.filter_by(id=acreditacion_id, empresa_id=empresa_id).first()
    if not acr:
        raise ValueError("Acreditación no encontrada")
    return _acr_dict(acr)


def _validar_refs(
    empresa_id: int,
    persona_id: int,
    programa_id: int,
    plan_id: int,
    curso_id: int,
) -> tuple[Participante, Curso]:
    persona = Participante.query.filter_by(id=persona_id, empresa_id=empresa_id, activo=True).first()
    if not persona:
        raise ValueError("Persona no válida")
    programa = ProgramaCapacitacion.query.filter_by(
        id=programa_id, empresa_id=empresa_id, activo=True
    ).first()
    if not programa:
        raise ValueError("Programa no válido")
    plan = ProgramaPlan.query.filter_by(id=plan_id, programa_id=programa_id).first()
    if not plan:
        raise ValueError("Plan no válido")
    curso = Curso.query.filter_by(id=curso_id, empresa_id=empresa_id, activo=True).first()
    if not curso:
        raise ValueError("Curso no válido")
    return persona, curso


def crear_acreditacion(empresa_id: int, data: dict) -> dict:
    persona_id = int(data["persona_id"])
    programa_id = int(data["programa_id"])
    plan_id = int(data["plan_id"])
    curso_id = int(data["curso_id"])
    persona, curso = _validar_refs(empresa_id, persona_id, programa_id, plan_id, curso_id)

    existente = Acreditacion.query.filter_by(
        persona_id=persona_id,
        programa_id=programa_id,
        plan_id=plan_id,
        curso_id=curso_id,
    ).first()
    if existente:
        raise ValueError("Ya existe una acreditación para esa combinación persona/programa/plan/curso")

    asistio = data.get("asistio")
    if asistio is None and "aprobo" in data:
        asistio = bool(data["aprobo"])
    nota = data.get("nota")
    aprobo = data.get("aprobo")
    if aprobo is None and asistio is not None:
        aprobo = calcular_aprobacion(asistio, nota, curso)
    aprobo = bool(aprobo) if aprobo is not None else False

    fecha_aprob = _parse_date(data.get("fecha_aprobacion"))
    if aprobo and not fecha_aprob:
        fecha_aprob = date.today()
    fecha_venc = _parse_date(data.get("fecha_vencimiento"))
    if aprobo and not fecha_venc:
        fecha_venc = calcular_fecha_vencimiento(True, fecha_aprob, curso)

    hoy = date.today()
    acr = Acreditacion(
        empresa_id=empresa_id,
        persona_id=persona.id,
        programa_id=programa_id,
        plan_id=plan_id,
        curso_id=curso_id,
        aprobo=aprobo,
        nota=nota,
        fecha_aprobacion=fecha_aprob if aprobo else None,
        fecha_vencimiento=fecha_venc if aprobo else None,
        horas_acreditadas=data.get("horas_acreditadas") or (curso.horas if aprobo else None),
        vigente=bool(aprobo and (fecha_venc is None or fecha_venc >= hoy)),
    )
    db.session.add(acr)
    db.session.commit()
    return _acr_dict(acr)


def actualizar_acreditacion(empresa_id: int, acreditacion_id: int, data: dict) -> dict:
    acr = Acreditacion.query.filter_by(id=acreditacion_id, empresa_id=empresa_id).first()
    if not acr:
        raise ValueError("Acreditación no encontrada")

    curso = acr.curso
    if "nota" in data:
        acr.nota = data["nota"]
    if "horas_acreditadas" in data:
        acr.horas_acreditadas = data["horas_acreditadas"]

    if "aprobo" in data:
        acr.aprobo = bool(data["aprobo"])
    elif "asistio" in data:
        acr.aprobo = bool(
            calcular_aprobacion(data["asistio"], acr.nota, curso)
        )

    if "fecha_aprobacion" in data:
        acr.fecha_aprobacion = _parse_date(data["fecha_aprobacion"])
    if "fecha_vencimiento" in data:
        acr.fecha_vencimiento = _parse_date(data["fecha_vencimiento"])
    elif acr.aprobo and acr.fecha_aprobacion and curso:
        acr.fecha_vencimiento = calcular_fecha_vencimiento(True, acr.fecha_aprobacion, curso)

    if acr.aprobo and not acr.fecha_aprobacion:
        acr.fecha_aprobacion = date.today()

    hoy = date.today()
    acr.vigente = bool(
        acr.aprobo and (acr.fecha_vencimiento is None or acr.fecha_vencimiento >= hoy)
    )
    db.session.commit()
    return _acr_dict(acr)


def eliminar_acreditacion(empresa_id: int, acreditacion_id: int) -> None:
    acr = Acreditacion.query.filter_by(id=acreditacion_id, empresa_id=empresa_id).first()
    if not acr:
        raise ValueError("Acreditación no encontrada")
    db.session.delete(acr)
    db.session.commit()


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
