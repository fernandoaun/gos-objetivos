from __future__ import annotations

from datetime import date

from gos.modulos.capacitacion.models import EncuentroCapacitacion, Participante
from gos.modulos.capacitacion.services.analitico_service import analitico_participante
from gos.modulos.objetivos.models.catalogos import Sector


def resumen_dashboard(empresa_id: int) -> dict:
    participantes = Participante.query.filter_by(empresa_id=empresa_id, activo=True).all()

    verde = rojo = gris = 0
    for p in participantes:
        data = analitico_participante(p.id, empresa_id=empresa_id)
        pendientes = data["resumen"]["total_pendientes"]
        if pendientes == 0:
            if data["resumen"]["total_cursos_realizados"] or data["resumen"]["total_certificaciones"]:
                verde += 1
            else:
                gris += 1
        else:
            rojo += 1

    total = len(participantes) or 1
    habilitados_pct = round(verde / total * 100) if participantes else 0
    inhabilitados_pct = round(rojo / total * 100) if participantes else 0

    sectores = Sector.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Sector.nombre).all()
    filas_sector = []
    for sector in sectores:
        del_sector = [p for p in participantes if p.sector_id == sector.id]
        s_v = s_r = s_g = 0
        for p in del_sector:
            data = analitico_participante(p.id, empresa_id=empresa_id)
            if data["resumen"]["total_pendientes"] == 0:
                if data["resumen"]["total_cursos_realizados"] or data["resumen"]["total_certificaciones"]:
                    s_v += 1
                else:
                    s_g += 1
            else:
                s_r += 1
        if del_sector:
            filas_sector.append(
                {
                    "id": sector.id,
                    "nombre": sector.nombre,
                    "verde": s_v,
                    "rojo": s_r,
                    "gris": s_g,
                }
            )

    from gos.modulos.capacitacion.models import CertificacionEmpleado, Curso

    cursos_activos = Curso.query.filter_by(empresa_id=empresa_id, activo=True).count()
    hoy = date.today()
    certs_vigentes = (
        CertificacionEmpleado.query.filter_by(empresa_id=empresa_id, vigente=True)
        .filter(
            (CertificacionEmpleado.fecha_vencimiento.is_(None))
            | (CertificacionEmpleado.fecha_vencimiento >= hoy)
        )
        .count()
    )
    certs_vencidas = (
        CertificacionEmpleado.query.filter_by(empresa_id=empresa_id)
        .filter(CertificacionEmpleado.fecha_vencimiento.isnot(None))
        .filter(CertificacionEmpleado.fecha_vencimiento < hoy)
        .count()
    )

    return {
        "recursos": [
            {
                "clave": "personal",
                "nombre": "Personal",
                "verde": verde,
                "rojo": rojo,
                "gris": gris,
            },
            {
                "clave": "sectores",
                "nombre": "Sectores",
                "verde": sum(f["verde"] for f in filas_sector),
                "rojo": sum(f["rojo"] for f in filas_sector),
                "gris": sum(f["gris"] for f in filas_sector),
            },
            {
                "clave": "certificaciones",
                "nombre": "Certificaciones",
                "verde": certs_vigentes,
                "rojo": certs_vencidas,
                "gris": max(0, cursos_activos - certs_vigentes - certs_vencidas),
            },
        ],
        "sectores": filas_sector,
        "habilitados_pct": habilitados_pct,
        "inhabilitados_pct": inhabilitados_pct,
        "totales": {
            "participantes": len(participantes),
            "encuentros_mes": 0,
        },
    }


def encuentros_calendario(empresa_id: int, desde: date, hasta: date) -> list[dict]:
    rows = (
        EncuentroCapacitacion.query.filter_by(empresa_id=empresa_id)
        .filter(EncuentroCapacitacion.fecha >= desde)
        .filter(EncuentroCapacitacion.fecha <= hasta)
        .order_by(EncuentroCapacitacion.fecha, EncuentroCapacitacion.hora_inicio)
        .all()
    )
    return [
        {
            "id": e.id,
            "titulo": e.titulo,
            "fecha": e.fecha.isoformat(),
            "hora_inicio": e.hora_inicio.isoformat() if e.hora_inicio else None,
            "hora_fin": e.hora_fin.isoformat() if e.hora_fin else None,
            "lugar": e.lugar,
            "instructor": e.instructor,
            "estado": e.estado,
            "programa_id": e.programa_id,
            "curso_id": e.curso_id,
        }
        for e in rows
    ]
