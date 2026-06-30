from __future__ import annotations

from datetime import date

from gos.modulos.capacitacion.models import (
    CertificacionEmpleado,
    Curso,
    Participante,
    PlanCapacitacion,
    RegistroCapacitacion,
    RequisitoFormacion,
)


def _requisitos_aplicables(participante: Participante) -> list[RequisitoFormacion]:
    """Requisitos por persona, puesto y sector (sin duplicar curso/cert)."""
    vistos: set[tuple[str, int]] = set()
    resultado: list[RequisitoFormacion] = []

    candidatos = RequisitoFormacion.query.filter_by(empresa_id=participante.empresa_id).all()
    for req in candidatos:
        aplica = False
        if req.participante_id == participante.id:
            aplica = True
        elif req.puesto_id and req.puesto_id == participante.puesto_id:
            aplica = True
        elif req.sector_id and req.sector_id == participante.sector_id:
            aplica = True

        if not aplica:
            continue

        if req.curso_id:
            clave = ("curso", req.curso_id)
        elif req.certificacion_tipo_id:
            clave = ("cert", req.certificacion_tipo_id)
        else:
            continue

        if clave in vistos:
            continue
        vistos.add(clave)
        resultado.append(req)

    return resultado


def _curso_cumplido(participante_id: int, curso_id: int, hoy: date) -> RegistroCapacitacion | None:
    registros = (
        RegistroCapacitacion.query.filter_by(
            participante_id=participante_id,
            curso_id=curso_id,
            aprobado=True,
        )
        .order_by(RegistroCapacitacion.fecha_realizacion.desc())
        .all()
    )
    for reg in registros:
        if reg.vigente_hasta and reg.vigente_hasta < hoy:
            continue
        return reg
    return None


def _cert_cumplida(participante_id: int, tipo_id: int, hoy: date) -> CertificacionEmpleado | None:
    certs = (
        CertificacionEmpleado.query.filter_by(
            participante_id=participante_id,
            tipo_id=tipo_id,
            vigente=True,
        )
        .order_by(CertificacionEmpleado.fecha_emision.desc())
        .all()
    )
    for cert in certs:
        if cert.fecha_vencimiento and cert.fecha_vencimiento < hoy:
            continue
        return cert
    return None


def analitico_participante(participante_id: int, empresa_id: int | None = None) -> dict:
    """
    Resumen analítico por persona:
    - cursos y certificaciones realizados (con notas)
    - requisitos pendientes
    - planificación (cuándo los realizará)
    """
    participante = Participante.query.get_or_404(participante_id)
    if empresa_id is not None and participante.empresa_id != empresa_id:
        raise ValueError("Participante no pertenece a la empresa indicada")

    hoy = date.today()

    realizados_cursos = []
    for reg in (
        RegistroCapacitacion.query.filter_by(participante_id=participante_id)
        .order_by(RegistroCapacitacion.fecha_realizacion.desc())
        .all()
    ):
        curso = reg.curso or Curso.query.get(reg.curso_id)
        realizados_cursos.append(
            {
                "registro_id": reg.id,
                "curso_id": reg.curso_id,
                "curso_codigo": curso.codigo if curso else None,
                "curso_nombre": curso.nombre if curso else None,
                "fecha_realizacion": reg.fecha_realizacion.isoformat(),
                "nota": float(reg.nota) if reg.nota is not None else None,
                "aprobado": reg.aprobado,
                "vigente_hasta": reg.vigente_hasta.isoformat() if reg.vigente_hasta else None,
                "observaciones": reg.observaciones,
                "tiene_certificado": bool(reg.certificado_path),
            }
        )

    realizados_certs = []
    for cert in (
        CertificacionEmpleado.query.filter_by(participante_id=participante_id)
        .order_by(CertificacionEmpleado.fecha_emision.desc())
        .all()
    ):
        tipo = cert.tipo
        vigente = cert.vigente and (
            cert.fecha_vencimiento is None or cert.fecha_vencimiento >= hoy
        )
        realizados_certs.append(
            {
                "certificacion_id": cert.id,
                "tipo_id": cert.tipo_id,
                "tipo_codigo": tipo.codigo if tipo else None,
                "tipo_nombre": tipo.nombre if tipo else None,
                "numero": cert.numero,
                "fecha_emision": cert.fecha_emision.isoformat(),
                "fecha_vencimiento": cert.fecha_vencimiento.isoformat()
                if cert.fecha_vencimiento
                else None,
                "vigente": vigente,
                "observaciones": cert.observaciones,
                "tiene_documento": bool(cert.documento_path),
            }
        )

    pendientes = []
    for req in _requisitos_aplicables(participante):
        if req.curso_id:
            cumplido = _curso_cumplido(participante_id, req.curso_id, hoy)
            if cumplido:
                continue
            curso = req.curso or Curso.query.get(req.curso_id)
            item = {
                "tipo": "curso",
                "curso_id": req.curso_id,
                "codigo": curso.codigo if curso else None,
                "nombre": curso.nombre if curso else None,
                "obligatorio": req.obligatorio,
                "origen_requisito": _origen_requisito(req, participante),
            }
        elif req.certificacion_tipo_id:
            cumplido = _cert_cumplida(participante_id, req.certificacion_tipo_id, hoy)
            if cumplido:
                continue
            tipo = req.certificacion_tipo
            item = {
                "tipo": "certificacion",
                "certificacion_tipo_id": req.certificacion_tipo_id,
                "codigo": tipo.codigo if tipo else None,
                "nombre": tipo.nombre if tipo else None,
                "obligatorio": req.obligatorio,
                "origen_requisito": _origen_requisito(req, participante),
            }
        else:
            continue
        pendientes.append(item)

    planes = []
    for plan in (
        PlanCapacitacion.query.filter_by(participante_id=participante_id)
        .filter(PlanCapacitacion.estado.in_(("pendiente", "programado")))
        .order_by(PlanCapacitacion.prioridad, PlanCapacitacion.fecha_planificada)
        .all()
    ):
        curso = plan.curso or Curso.query.get(plan.curso_id)
        encuentro = plan.encuentro
        fecha_efectiva = plan.fecha_planificada
        if encuentro and encuentro.fecha:
            fecha_efectiva = encuentro.fecha

        planes.append(
            {
                "plan_id": plan.id,
                "curso_id": plan.curso_id,
                "curso_codigo": curso.codigo if curso else None,
                "curso_nombre": curso.nombre if curso else None,
                "estado": plan.estado,
                "fecha_planificada": fecha_efectiva.isoformat() if fecha_efectiva else None,
                "encuentro_id": plan.encuentro_id,
                "encuentro_titulo": encuentro.titulo if encuentro else None,
                "programa_id": plan.programa_id,
                "prioridad": plan.prioridad,
                "observaciones": plan.observaciones,
            }
        )

    pendientes_sin_plan = []
    cursos_planificados = {p["curso_id"] for p in planes if p.get("curso_id")}
    for item in pendientes:
        if item.get("tipo") == "curso" and item.get("curso_id") not in cursos_planificados:
            pendientes_sin_plan.append(item)

    return {
        "participante": {
            "id": participante.id,
            "nombre": participante.nombre,
            "legajo": participante.legajo,
            "tiene_foto": bool(participante.foto_path),
            "sector_id": participante.sector_id,
            "sector_nombre": participante.sector.nombre if participante.sector else None,
            "puesto_id": participante.puesto_id,
            "puesto_nombre": participante.puesto.nombre if participante.puesto else None,
        },
        "cursos_realizados": realizados_cursos,
        "certificaciones": realizados_certs,
        "pendientes": pendientes,
        "pendientes_sin_planificar": pendientes_sin_plan,
        "planificacion": planes,
        "resumen": {
            "total_cursos_realizados": len(realizados_cursos),
            "total_certificaciones": len(realizados_certs),
            "total_pendientes": len(pendientes),
            "total_sin_planificar": len(pendientes_sin_plan),
        },
    }


def _origen_requisito(req: RequisitoFormacion, participante: Participante) -> str:
    if req.participante_id == participante.id:
        return "persona"
    if req.puesto_id == participante.puesto_id:
        return "puesto"
    if req.sector_id == participante.sector_id:
        return "sector"
    return "otro"
