from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from gos.modulos.capacitacion.models import (
    CertificacionEmpleado,
    Curso,
    EncuentroCapacitacion,
    Participante,
    PlanCapacitacion,
    RegistroCapacitacion,
)
from gos.modulos.capacitacion.services.analitico_service import analitico_participante
from gos.modulos.capacitacion.services.taxonomia_service import etiqueta_taxonomia
from gos.modulos.capacitacion.services.config_service import dias_proximo_vencer
from gos.modulos.objetivos.models.catalogos import Sector


def resumen_dashboard(empresa_id: int, *, sector_id: int | None = None) -> dict:
    participantes_q = Participante.query.filter_by(empresa_id=empresa_id, activo=True)
    if sector_id:
        participantes_q = participantes_q.filter_by(sector_id=sector_id)
    participantes = participantes_q.all()

    hoy = date.today()
    dias_umbral = dias_proximo_vencer(empresa_id)
    inicio_mes = hoy.replace(day=1)
    _, ultimo = monthrange(hoy.year, hoy.month)
    fin_mes = hoy.replace(day=ultimo)

    verde = rojo = gris = amarillo = 0
    pendientes_total = 0
    obligatorias_pendientes = 0
    proximas_vencer = 0
    vencidas = 0
    horas_mes = 0.0
    aprobados = 0
    evaluados = 0

    cumplimiento_por_sector: dict[int, dict] = {}
    cumplimiento_por_curso: dict[int, dict] = defaultdict(lambda: {"ok": 0, "total": 0, "nombre": ""})
    cumplimiento_por_tipo: dict[str, dict] = defaultdict(lambda: {"ok": 0, "total": 0, "nombre": ""})
    cumplimiento_por_persona: list[dict] = []
    ranking_vencimientos: dict[int, dict] = defaultdict(lambda: {"count": 0, "nombre": "", "codigo": ""})

    for p in participantes:
        data = analitico_participante(p.id, empresa_id=empresa_id)
        pend = data["resumen"]["total_pendientes"]
        pendientes_total += pend
        for item in data["pendientes"]:
            if item.get("obligatorio"):
                obligatorias_pendientes += 1
            if item.get("tipo") == "curso" and item.get("curso_id"):
                curso = Curso.query.get(item["curso_id"])
                tipo_key = (curso.categoria if curso and curso.categoria else curso.tipo_capacitacion if curso else None) or "sin_categoria"
                cumplimiento_por_tipo[tipo_key]["total"] += 1
                cumplimiento_por_tipo[tipo_key]["nombre"] = (
                    etiqueta_taxonomia(empresa_id, "categoria", tipo_key) or tipo_key
                )

        for reg in data["cursos_realizados"]:
            cid = reg.get("curso_id")
            if cid:
                curso = Curso.query.get(cid)
                tipo_key = (curso.categoria if curso and curso.categoria else curso.tipo_capacitacion if curso else None) or "sin_categoria"
                cumplimiento_por_tipo[tipo_key]["total"] += 1
                cumplimiento_por_tipo[tipo_key]["ok"] += 1
                cumplimiento_por_tipo[tipo_key]["nombre"] = (
                    etiqueta_taxonomia(empresa_id, "categoria", tipo_key) or tipo_key
                )

        for reg in data["cursos_realizados"]:
            if reg.get("vigente_hasta"):
                fv = date.fromisoformat(reg["vigente_hasta"])
                if fv < hoy:
                    vencidas += 1
                    cid = reg.get("curso_id")
                    if cid:
                        ranking_vencimientos[cid]["count"] += 1
                        ranking_vencimientos[cid]["nombre"] = reg.get("curso_nombre") or ""
                        ranking_vencimientos[cid]["codigo"] = reg.get("curso_codigo") or ""
                elif fv <= hoy + timedelta(days=dias_umbral):
                    proximas_vencer += 1

        if pend == 0:
            if data["resumen"]["total_cursos_realizados"] or data["resumen"]["total_certificaciones"]:
                verde += 1
            else:
                gris += 1
        else:
            rojo += 1

        total_req = data["resumen"]["total_cursos_realizados"] + pend
        pct_persona = round((data["resumen"]["total_cursos_realizados"] / total_req) * 100) if total_req else 100
        cumplimiento_por_persona.append(
            {"id": p.id, "nombre": p.nombre_completo, "pct": pct_persona, "pendientes": pend}
        )

        sid = p.sector_id or 0
        if sid not in cumplimiento_por_sector:
            cumplimiento_por_sector[sid] = {"ok": 0, "total": 0, "nombre": p.sector.nombre if p.sector else "Sin sector"}
        cumplimiento_por_sector[sid]["total"] += 1
        if pend == 0 and (data["resumen"]["total_cursos_realizados"] or data["resumen"]["total_certificaciones"]):
            cumplimiento_por_sector[sid]["ok"] += 1

    registros_mes = (
        RegistroCapacitacion.query.filter_by(empresa_id=empresa_id)
        .filter(RegistroCapacitacion.fecha_realizacion >= inicio_mes)
        .filter(RegistroCapacitacion.fecha_realizacion <= fin_mes)
        .all()
    )
    realizadas_mes = len(registros_mes)
    for r in registros_mes:
        if r.horas:
            horas_mes += float(r.horas)
        if r.nota is not None:
            evaluados += 1
            if r.aprobado:
                aprobados += 1
        cid = r.curso_id
        cumplimiento_por_curso[cid]["ok"] += 1 if r.aprobado else 0
        cumplimiento_por_curso[cid]["total"] += 1
        if r.curso:
            cumplimiento_por_curso[cid]["nombre"] = r.curso.nombre

    cursos_activos = Curso.query.filter_by(empresa_id=empresa_id, activo=True).count()
    encuentros_mes = (
        EncuentroCapacitacion.query.filter_by(empresa_id=empresa_id)
        .filter(EncuentroCapacitacion.fecha >= inicio_mes)
        .filter(EncuentroCapacitacion.fecha <= fin_mes)
        .count()
    )

    total = len(participantes) or 1
    cumplimiento_general = round(verde / total * 100) if participantes else 0
    tasa_aprobacion = round(aprobados / evaluados * 100) if evaluados else 0

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
            filas_sector.append({"id": sector.id, "nombre": sector.nombre, "verde": s_v, "rojo": s_r, "gris": s_g})

    certs_vigentes = (
        CertificacionEmpleado.query.filter_by(empresa_id=empresa_id, vigente=True)
        .filter(
            (CertificacionEmpleado.fecha_vencimiento.is_(None))
            | (CertificacionEmpleado.fecha_vencimiento >= hoy)
        )
        .count()
    )
    certs_vencidas_count = (
        CertificacionEmpleado.query.filter_by(empresa_id=empresa_id)
        .filter(CertificacionEmpleado.fecha_vencimiento.isnot(None))
        .filter(CertificacionEmpleado.fecha_vencimiento < hoy)
        .count()
    )

    evolucion = _evolucion_mensual(empresa_id, meses=6)
    ranking = sorted(
        [{"curso_id": k, **v} for k, v in ranking_vencimientos.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return {
        "kpis": {
            "personas_activas": len(participantes),
            "cursos_cargados": cursos_activos,
            "realizadas_mes": realizadas_mes,
            "pendientes": pendientes_total,
            "vencidas": vencidas + certs_vencidas_count,
            "proximas_vencer": proximas_vencer,
            "cumplimiento_general": cumplimiento_general,
            "horas_hombre_mes": round(horas_mes, 1),
            "tasa_aprobacion": tasa_aprobacion,
            "obligatorias_pendientes": obligatorias_pendientes,
            "encuentros_mes": encuentros_mes,
        },
        "recursos": [
            {"clave": "personal", "nombre": "Personal", "verde": verde, "rojo": rojo, "gris": gris, "amarillo": amarillo},
            {
                "clave": "certificaciones",
                "nombre": "Certificaciones",
                "verde": certs_vigentes,
                "rojo": certs_vencidas_count,
                "gris": max(0, cursos_activos - certs_vigentes - certs_vencidas_count),
            },
        ],
        "sectores": filas_sector,
        "cumplimiento_por_sector": [
            {
                "sector_id": k,
                "nombre": v["nombre"],
                "pct": round(v["ok"] / v["total"] * 100) if v["total"] else 0,
            }
            for k, v in cumplimiento_por_sector.items()
            if v["total"] > 0
        ],
        "cumplimiento_por_curso": [
            {"curso_id": k, "nombre": v["nombre"], "pct": round(v["ok"] / v["total"] * 100) if v["total"] else 0}
            for k, v in cumplimiento_por_curso.items()
            if v["total"] > 0
        ],
        "cumplimiento_por_tipo": [
            {
                "tipo": k,
                "nombre": v["nombre"] or k,
                "pct": round(v["ok"] / v["total"] * 100) if v["total"] else 0,
                "ok": v["ok"],
                "total": v["total"],
            }
            for k, v in cumplimiento_por_tipo.items()
            if v["total"] > 0
        ],
        "cumplimiento_por_persona": sorted(cumplimiento_por_persona, key=lambda x: x["pct"])[:15],
        "ranking_vencimientos": ranking,
        "evolucion_mensual": evolucion,
        "habilitados_pct": round(verde / total * 100) if participantes else 0,
        "inhabilitados_pct": round(rojo / total * 100) if participantes else 0,
        "totales": {"participantes": len(participantes), "encuentros_mes": encuentros_mes},
    }


def _evolucion_mensual(empresa_id: int, meses: int = 6) -> list[dict]:
    hoy = date.today()
    resultado = []
    for i in range(meses - 1, -1, -1):
        m = hoy.month - i
        y = hoy.year
        while m <= 0:
            m += 12
            y -= 1
        _, ult = monthrange(y, m)
        desde = date(y, m, 1)
        hasta = date(y, m, ult)
        count = (
            RegistroCapacitacion.query.filter_by(empresa_id=empresa_id)
            .filter(RegistroCapacitacion.fecha_realizacion >= desde)
            .filter(RegistroCapacitacion.fecha_realizacion <= hasta)
            .count()
        )
        resultado.append({"mes": f"{y}-{m:02d}", "realizadas": count})
    return resultado


def encuentros_cronograma(empresa_id: int, desde: date, hasta: date) -> list[dict]:
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
            "link_virtual": e.link_virtual,
            "instructor": e.instructor,
            "estado": e.estado,
            "programa_id": e.programa_id,
            "curso_id": e.curso_id,
        }
        for e in rows
    ]
