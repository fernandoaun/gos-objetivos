from __future__ import annotations

from datetime import date, timedelta

from gos.modulos.capacitacion.models import (
    CertificacionEmpleado,
    CertificacionTipo,
    Curso,
    Participante,
    RegistroCapacitacion,
)
from gos.modulos.capacitacion.services.analitico_service import (
    _cert_cumplida,
    _curso_cumplido,
    _requisitos_aplicables,
    analitico_participante,
)
from gos.modulos.capacitacion.services.config_service import dias_proximo_vencer

NORMAS_ISO = {
    "9001": {
        "titulo": "ISO 9001 — Gestión de la Calidad",
        "tipos_curso": ("sgi", "normativa"),
        "patrones": ("9001", "sgi", "calidad", "iso9"),
    },
    "14001": {
        "titulo": "ISO 14001 — Gestión Ambiental",
        "tipos_curso": ("hse", "normativa"),
        "patrones": ("14001", "ambient", "medio", "iso14"),
    },
    "45001": {
        "titulo": "ISO 45001 — Seguridad y Salud Ocupacional",
        "tipos_curso": ("hse", "obligatoria"),
        "patrones": ("45001", "sst", "seguridad", "iso45", "hse"),
    },
}


def _coincide_norma(texto: str | None, patrones: tuple[str, ...]) -> bool:
    if not texto:
        return False
    t = texto.lower()
    return any(p in t for p in patrones)


def cursos_para_norma(empresa_id: int, norma: str) -> list[Curso]:
    cfg = NORMAS_ISO.get(norma)
    if not cfg:
        raise ValueError("Norma ISO inválida (use 9001, 14001 o 45001)")
    cursos = Curso.query.filter_by(empresa_id=empresa_id, activo=True).all()
    resultado = []
    for c in cursos:
        if c.tipo_capacitacion in cfg["tipos_curso"]:
            resultado.append(c)
        elif _coincide_norma(c.codigo, cfg["patrones"]) or _coincide_norma(c.nombre, cfg["patrones"]):
            resultado.append(c)
    return resultado


def tipos_cert_para_norma(empresa_id: int, norma: str) -> list[CertificacionTipo]:
    cfg = NORMAS_ISO.get(norma)
    if not cfg:
        raise ValueError("Norma ISO inválida (use 9001, 14001 o 45001)")
    tipos = CertificacionTipo.query.filter_by(empresa_id=empresa_id, activo=True).all()
    return [
        t
        for t in tipos
        if _coincide_norma(t.codigo, cfg["patrones"]) or _coincide_norma(t.nombre, cfg["patrones"])
    ]


def _estado_requisito_curso(participante_id: int, curso_id: int, hoy: date, dias_umbral: int) -> str:
    reg = _curso_cumplido(participante_id, curso_id, hoy)
    if not reg:
        return "pendiente"
    if reg.vigente_hasta and reg.vigente_hasta < hoy:
        return "vencido"
    if reg.vigente_hasta and reg.vigente_hasta <= hoy + timedelta(days=dias_umbral):
        return "proximo_vencer"
    return "cumplido"


def _estado_requisito_cert(participante_id: int, tipo_id: int, hoy: date) -> str:
    cert = _cert_cumplida(participante_id, tipo_id, hoy)
    if not cert:
        return "pendiente"
    if cert.fecha_vencimiento and cert.fecha_vencimiento < hoy:
        return "vencido"
    return "cumplido"


def reporte_iso(empresa_id: int, norma: str) -> dict:
    if norma not in NORMAS_ISO:
        raise ValueError("Norma ISO inválida (use 9001, 14001 o 45001)")

    cfg = NORMAS_ISO[norma]
    hoy = date.today()
    dias_umbral = dias_proximo_vencer(empresa_id)
    curso_ids = {c.id for c in cursos_para_norma(empresa_id, norma)}
    tipo_ids = {t.id for t in tipos_cert_para_norma(empresa_id, norma)}

    participantes = Participante.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Participante.nombre).all()
    filas_personas = []
    total_req = cumplidos = pendientes = vencidos = 0

    for p in participantes:
        requisitos_norma = []
        for req in _requisitos_aplicables(p):
            if req.curso_id and req.curso_id in curso_ids:
                curso = req.curso or Curso.query.get(req.curso_id)
                estado = _estado_requisito_curso(p.id, req.curso_id, hoy, dias_umbral)
                reg = _curso_cumplido(p.id, req.curso_id, hoy) or RegistroCapacitacion.query.filter_by(
                    participante_id=p.id, curso_id=req.curso_id, aprobado=True
                ).order_by(RegistroCapacitacion.fecha_realizacion.desc()).first()
                item = {
                    "tipo": "curso",
                    "curso_id": req.curso_id,
                    "codigo": curso.codigo if curso else None,
                    "nombre": curso.nombre if curso else None,
                    "obligatorio": req.obligatorio,
                    "estado": estado,
                    "fecha_realizacion": reg.fecha_realizacion.isoformat() if reg else None,
                    "vigente_hasta": reg.vigente_hasta.isoformat() if reg and reg.vigente_hasta else None,
                    "tiene_certificado": bool(reg and reg.certificado_path),
                    "registro_id": reg.id if reg else None,
                }
                requisitos_norma.append(item)
            elif req.certificacion_tipo_id and req.certificacion_tipo_id in tipo_ids:
                tipo = req.certificacion_tipo or CertificacionTipo.query.get(req.certificacion_tipo_id)
                estado = _estado_requisito_cert(p.id, req.certificacion_tipo_id, hoy)
                cert = _cert_cumplida(p.id, req.certificacion_tipo_id, hoy) or CertificacionEmpleado.query.filter_by(
                    participante_id=p.id, tipo_id=req.certificacion_tipo_id
                ).order_by(CertificacionEmpleado.fecha_emision.desc()).first()
                item = {
                    "tipo": "certificacion",
                    "tipo_id": req.certificacion_tipo_id,
                    "codigo": tipo.codigo if tipo else None,
                    "nombre": tipo.nombre if tipo else None,
                    "obligatorio": req.obligatorio,
                    "estado": estado,
                    "fecha_emision": cert.fecha_emision.isoformat() if cert else None,
                    "fecha_vencimiento": cert.fecha_vencimiento.isoformat() if cert and cert.fecha_vencimiento else None,
                    "tiene_documento": bool(cert and cert.documento_path),
                    "certificacion_id": cert.id if cert else None,
                }
                requisitos_norma.append(item)

        if not requisitos_norma:
            continue

        for r in requisitos_norma:
            total_req += 1
            if r["estado"] == "cumplido":
                cumplidos += 1
            elif r["estado"] == "vencido":
                vencidos += 1
            elif r["estado"] in ("pendiente", "proximo_vencer"):
                pendientes += 1

        pct = round(sum(1 for r in requisitos_norma if r["estado"] == "cumplido") / len(requisitos_norma) * 100)
        filas_personas.append(
            {
                "id": p.id,
                "nombre": p.nombre_completo,
                "legajo": p.legajo,
                "sector": p.sector.nombre if p.sector else None,
                "puesto": p.puesto.nombre if p.puesto else None,
                "cumplimiento_pct": pct,
                "requisitos": requisitos_norma,
            }
        )

    cumplimiento_pct = round(cumplidos / total_req * 100) if total_req else 100

    return {
        "norma": norma,
        "titulo": cfg["titulo"],
        "fecha_generacion": hoy.isoformat(),
        "resumen": {
            "personas_evaluadas": len(filas_personas),
            "requisitos_total": total_req,
            "cumplidos": cumplidos,
            "pendientes": pendientes,
            "vencidos": vencidos,
            "cumplimiento_pct": cumplimiento_pct,
        },
        "cursos_norma": [
            {"id": c.id, "codigo": c.codigo, "nombre": c.nombre, "tipo": c.tipo_capacitacion}
            for c in cursos_para_norma(empresa_id, norma)
        ],
        "personas": filas_personas,
    }


def resumen_general_auditoria(empresa_id: int) -> dict:
    normas = {}
    for codigo in NORMAS_ISO:
        try:
            normas[codigo] = reporte_iso(empresa_id, codigo)["resumen"]
        except ValueError:
            pass

    participantes = Participante.query.filter_by(empresa_id=empresa_id, activo=True).count()
    pendientes_globales = 0
    for p in Participante.query.filter_by(empresa_id=empresa_id, activo=True).all():
        data = analitico_participante(p.id, empresa_id=empresa_id)
        pendientes_globales += data["resumen"]["total_pendientes"]

    return {
        "fecha": date.today().isoformat(),
        "participantes_activos": participantes,
        "pendientes_globales": pendientes_globales,
        "normas_iso": normas,
    }
