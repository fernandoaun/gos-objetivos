"""CRUD de planes de capacitación por persona (cap_planes)."""

from __future__ import annotations

from datetime import date

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    Curso,
    EncuentroCapacitacion,
    Participante,
    PlanCapacitacion,
    ProgramaCapacitacion,
)


def _plan_dict(plan: PlanCapacitacion) -> dict:
    curso = plan.curso
    encuentro = plan.encuentro
    fecha_efectiva = plan.fecha_planificada
    if encuentro and encuentro.fecha:
        fecha_efectiva = encuentro.fecha
    return {
        "id": plan.id,
        "participante_id": plan.participante_id,
        "curso_id": plan.curso_id,
        "curso_codigo": curso.codigo if curso else None,
        "curso_nombre": curso.nombre if curso else None,
        "programa_id": plan.programa_id,
        "encuentro_id": plan.encuentro_id,
        "encuentro_titulo": encuentro.titulo if encuentro else None,
        "fecha_planificada": fecha_efectiva.isoformat() if fecha_efectiva else None,
        "estado": plan.estado,
        "prioridad": plan.prioridad,
        "observaciones": plan.observaciones,
    }


def listar_planes_participante(empresa_id: int, participante_id: int) -> list[dict]:
    participante = Participante.query.filter_by(
        id=participante_id, empresa_id=empresa_id, activo=True
    ).first()
    if not participante:
        raise ValueError("Participante no encontrado")
    planes = (
        PlanCapacitacion.query.filter_by(participante_id=participante_id, empresa_id=empresa_id)
        .filter(PlanCapacitacion.estado.in_(("pendiente", "programado")))
        .order_by(PlanCapacitacion.prioridad, PlanCapacitacion.fecha_planificada)
        .all()
    )
    return [_plan_dict(p) for p in planes]


def crear_plan_capacitacion(empresa_id: int, participante_id: int, data: dict) -> dict:
    participante = Participante.query.filter_by(
        id=participante_id, empresa_id=empresa_id, activo=True
    ).first()
    if not participante:
        raise ValueError("Participante no encontrado")

    curso_id = int(data["curso_id"])
    curso = Curso.query.filter_by(id=curso_id, empresa_id=empresa_id, activo=True).first()
    if not curso:
        raise ValueError("Curso no válido")

    programa_id = data.get("programa_id")
    if programa_id:
        programa_id = int(programa_id)
        if not ProgramaCapacitacion.query.filter_by(
            id=programa_id, empresa_id=empresa_id, activo=True
        ).first():
            raise ValueError("Programa no válido")

    encuentro_id = data.get("encuentro_id")
    fecha_planificada = _parse_date(data.get("fecha_planificada"))
    estado = "programado" if encuentro_id or fecha_planificada else "pendiente"
    if encuentro_id:
        encuentro_id = int(encuentro_id)
        enc = EncuentroCapacitacion.query.filter_by(
            id=encuentro_id, empresa_id=empresa_id
        ).first()
        if not enc:
            raise ValueError("Encuentro no válido")
        if not fecha_planificada and enc.fecha:
            fecha_planificada = enc.fecha
        estado = "programado"

    dup = (
        PlanCapacitacion.query.filter_by(
            participante_id=participante_id,
            curso_id=curso_id,
            empresa_id=empresa_id,
        )
        .filter(PlanCapacitacion.estado.in_(("pendiente", "programado")))
        .first()
    )
    if dup:
        raise ValueError("Ya hay un plan activo para este curso")

    plan = PlanCapacitacion(
        empresa_id=empresa_id,
        participante_id=participante_id,
        curso_id=curso_id,
        programa_id=programa_id,
        encuentro_id=encuentro_id,
        fecha_planificada=fecha_planificada,
        estado=estado,
        prioridad=int(data.get("prioridad") or 1),
        observaciones=(data.get("observaciones") or "").strip() or None,
    )
    db.session.add(plan)
    db.session.commit()
    return _plan_dict(plan)


def actualizar_plan_capacitacion(empresa_id: int, plan_id: int, data: dict) -> dict:
    plan = PlanCapacitacion.query.filter_by(id=plan_id, empresa_id=empresa_id).first()
    if not plan:
        raise ValueError("Plan no encontrado")
    if plan.estado not in ("pendiente", "programado"):
        raise ValueError("Solo se pueden editar planes pendientes o programados")

    if "encuentro_id" in data:
        encuentro_id = data.get("encuentro_id")
        if encuentro_id:
            encuentro_id = int(encuentro_id)
            enc = EncuentroCapacitacion.query.filter_by(
                id=encuentro_id, empresa_id=empresa_id
            ).first()
            if not enc:
                raise ValueError("Encuentro no válido")
            plan.encuentro_id = encuentro_id
            if enc.fecha:
                plan.fecha_planificada = enc.fecha
            plan.estado = "programado"
        else:
            plan.encuentro_id = None
            plan.estado = "pendiente" if not plan.fecha_planificada else "programado"

    if "fecha_planificada" in data:
        plan.fecha_planificada = _parse_date(data["fecha_planificada"])
        if plan.fecha_planificada and not plan.encuentro_id:
            plan.estado = "programado"

    if "prioridad" in data:
        plan.prioridad = int(data["prioridad"])
    if "observaciones" in data:
        plan.observaciones = (data["observaciones"] or "").strip() or None
    if "estado" in data and data["estado"] in ("pendiente", "programado"):
        plan.estado = data["estado"]

    db.session.commit()
    return _plan_dict(plan)


def cancelar_plan_capacitacion(empresa_id: int, plan_id: int) -> None:
    plan = PlanCapacitacion.query.filter_by(id=plan_id, empresa_id=empresa_id).first()
    if not plan:
        raise ValueError("Plan no encontrado")
    plan.estado = "cancelado"
    plan.encuentro_id = None
    db.session.commit()


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
