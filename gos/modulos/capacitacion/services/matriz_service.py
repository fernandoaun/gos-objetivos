from __future__ import annotations

from datetime import date, timedelta

from gos.modulos.capacitacion.models import (
    Curso,
    Participante,
    PlanCapacitacion,
    RegistroCapacitacion,
)
from gos.modulos.capacitacion.services.analitico_service import _requisitos_aplicables
from gos.modulos.capacitacion.services.config_service import dias_proximo_vencer

ESTADOS_MATRIZ = (
    "pendiente",
    "programada",
    "realizada",
    "aprobada",
    "vencida",
    "no_aplica",
)

DIAS_PROXIMO_VENCER = 30


def _curso_requerido(participante: Participante, curso_id: int) -> bool:
    for req in _requisitos_aplicables(participante):
        if req.curso_id == curso_id:
            return True
    return False


def _ultimo_registro(participante_id: int, curso_id: int) -> RegistroCapacitacion | None:
    return (
        RegistroCapacitacion.query.filter_by(participante_id=participante_id, curso_id=curso_id)
        .order_by(RegistroCapacitacion.fecha_realizacion.desc())
        .first()
    )


def _plan_activo(participante_id: int, curso_id: int) -> PlanCapacitacion | None:
    return (
        PlanCapacitacion.query.filter_by(participante_id=participante_id, curso_id=curso_id)
        .filter(PlanCapacitacion.estado.in_(("pendiente", "programado")))
        .order_by(PlanCapacitacion.fecha_planificada)
        .first()
    )


def _estado_celda(participante: Participante, curso: Curso, hoy: date) -> dict:
    requerido = _curso_requerido(participante, curso.id)
    if not requerido:
        return {
            "estado": "no_aplica",
            "color": "gris",
            "fecha_realizacion": None,
            "fecha_vencimiento": None,
            "nota": None,
            "certificado": None,
        }

    reg = _ultimo_registro(participante.id, curso.id)
    plan = _plan_activo(participante.id, curso.id)
    dias_umbral = dias_proximo_vencer(participante.empresa_id)

    if reg and reg.aprobado:
        vigente_hasta = reg.vigente_hasta
        if vigente_hasta and vigente_hasta < hoy:
            return _celda_dict("vencida", "rojo", reg)
        if vigente_hasta and vigente_hasta <= hoy + timedelta(days=dias_umbral):
            return _celda_dict("aprobada", "amarillo", reg)
        return _celda_dict("aprobada", "verde", reg)

    if reg and not reg.aprobado:
        return _celda_dict("realizada", "amarillo", reg)

    if plan:
        return {
            "estado": "programada",
            "color": "azul",
            "fecha_realizacion": None,
            "fecha_vencimiento": None,
            "nota": None,
            "certificado": None,
            "fecha_programada": plan.fecha_planificada.isoformat() if plan.fecha_planificada else None,
        }

    nivel = "rojo" if _es_obligatorio(participante, curso.id) else "amarillo"
    return {
        "estado": "pendiente",
        "color": nivel,
        "fecha_realizacion": None,
        "fecha_vencimiento": None,
        "nota": None,
        "certificado": None,
    }


def _es_obligatorio(participante: Participante, curso_id: int) -> bool:
    for req in _requisitos_aplicables(participante):
        if req.curso_id == curso_id and req.obligatorio:
            return True
    return False


def _celda_dict(estado: str, color: str, reg: RegistroCapacitacion) -> dict:
    return {
        "estado": estado,
        "color": color,
        "fecha_realizacion": reg.fecha_realizacion.isoformat(),
        "fecha_vencimiento": reg.vigente_hasta.isoformat() if reg.vigente_hasta else None,
        "nota": float(reg.nota) if reg.nota is not None else None,
        "certificado": reg.certificado_path,
    }


def matriz_capacitaciones(
    empresa_id: int,
    *,
    sector_id: int | None = None,
    puesto_id: int | None = None,
    curso_id: int | None = None,
    participante_id: int | None = None,
    estado: str | None = None,
    solo_requeridos: bool = True,
) -> dict:
    hoy = date.today()

    pq = Participante.query.filter_by(empresa_id=empresa_id, activo=True)
    if sector_id:
        pq = pq.filter_by(sector_id=sector_id)
    if puesto_id:
        pq = pq.filter_by(puesto_id=puesto_id)
    if participante_id:
        pq = pq.filter_by(id=participante_id)
    participantes = pq.order_by(Participante.nombre).all()

    cq = Curso.query.filter_by(empresa_id=empresa_id, activo=True)
    if curso_id:
        cq = cq.filter_by(id=curso_id)
    cursos = cq.order_by(Curso.codigo).all()

    filas = []
    for p in participantes:
        celdas = {}
        for c in cursos:
            if solo_requeridos and not _curso_requerido(p, c.id):
                continue
            celda = _estado_celda(p, c, hoy)
            if estado and celda["estado"] != estado:
                continue
            celdas[str(c.id)] = celda
        if solo_requeridos and not celdas:
            continue
        filas.append(
            {
                "participante_id": p.id,
                "nombre": p.nombre_completo if hasattr(p, "nombre_completo") else p.nombre,
                "legajo": p.legajo,
                "sector_id": p.sector_id,
                "sector_nombre": p.sector.nombre if p.sector else None,
                "puesto_nombre": p.puesto.nombre if p.puesto else None,
                "celdas": celdas,
            }
        )

    columnas = [
        {"id": c.id, "codigo": c.codigo, "nombre": c.nombre, "tipo": c.tipo_capacitacion}
        for c in cursos
        if not solo_requeridos or any(str(c.id) in f["celdas"] for f in filas)
    ]

    return {
        "columnas": columnas,
        "filas": filas,
        "leyenda": {
            "verde": "Vigente / aprobado",
            "amarillo": "Próximo a vencer / pendiente",
            "rojo": "Vencido / pendiente crítico",
            "azul": "Programado",
            "gris": "No aplica",
        },
    }
