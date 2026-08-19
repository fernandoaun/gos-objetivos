from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from gos.modulos.capacitacion.models import (
    Acreditacion,
    AsistenciaEncuentro,
    CertificacionEmpleado,
    Curso,
    EncuentroCapacitacion,
    Participante,
    RegistroCapacitacion,
)
from gos.modulos.capacitacion.services.analitico_service import analitico_participante
from gos.modulos.capacitacion.services.taxonomia_service import etiqueta_taxonomia
from gos.modulos.capacitacion.services.config_service import dias_proximo_vencer
from gos.modulos.objetivos.models.catalogos import Sector


def _fin_de_mes(d: date) -> date:
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def _cursos_ok_de_analitico(data: dict, hoy: date) -> set[int]:
    ok: set[int] = set()
    for reg in data.get("cursos_realizados") or []:
        if not reg.get("aprobado") or not reg.get("curso_id"):
            continue
        if reg.get("vigente_hasta") and date.fromisoformat(reg["vigente_hasta"]) < hoy:
            continue
        ok.add(reg["curso_id"])
    return ok


def _flag_true(v) -> bool:
    """SQLite may persist booleans as 0/1; `is True` would miss them."""
    return v is True or v == 1


def _flag_false(v) -> bool:
    return v is False or v == 0


def _asignacion_cumplida(asist, acr, hoy: date) -> bool:
    if acr and _flag_true(acr.aprobo) and (acr.fecha_vencimiento is None or acr.fecha_vencimiento >= hoy):
        return True
    return _flag_true(asist.aprobado)


def _desaprobo_explicito(asist, acr) -> bool:
    if _flag_false(asist.aprobado):
        return True
    if acr is None:
        return False
    # Acreditacion.aprobo defaults to False (non-null). Only a real evaluation counts.
    if _flag_true(acr.aprobo):
        return False
    return acr.nota is not None or acr.fecha_aprobacion is not None


def _encuentro_se_dictó(enc, asist) -> bool:
    """Roster-only inscription on a session that never ran is not a missed deadline."""
    estado = (getattr(enc, "estado", None) or "").lower()
    if estado in ("cerrado", "realizado", "en_curso"):
        return True
    if getattr(enc, "fecha_realizacion", None):
        return True
    return asist.asistencia in ("presente", "ausente")


def _asignacion_inhabilita(asist, enc, acr, hoy: date, cursos_ok: set[int]) -> bool:
    """Solo inhabilita un curso programado desaprobado o vencido sin aprobar.

    Huecos de catálogo (RequisitoFormacion / programa) no inhabilitan.
    Inscripto en un encuentro aún planificado —aunque el mes ya pasó— tampoco:
    suele ser inscripción masiva al cronograma, no un desaprobado.
    """
    estado = (getattr(enc, "estado", None) or "").lower()
    if estado in ("cancelado", "reprogramado"):
        return False
    if getattr(enc, "es_buenas_practicas", False):
        return False
    if enc.curso_id and enc.curso_id in cursos_ok:
        return False
    if _asignacion_cumplida(asist, acr, hoy):
        return False
    if _desaprobo_explicito(asist, acr):
        return True
    mes_vencido = bool(enc.fecha and _fin_de_mes(enc.fecha) < hoy)
    return mes_vencido and _encuentro_se_dictó(enc, asist)


def persona_habilitada_por_programados(asignaciones: list, hoy: date, cursos_ok: set[int]) -> bool:
    """Habilitada por defecto; deja de estarlo si un curso programado falló o venció."""
    for asist, enc, acr in asignaciones:
        if _asignacion_inhabilita(asist, enc, acr, hoy, cursos_ok):
            return False
    return True


def _programados_por_persona(participante_ids: list[int]) -> dict[int, list]:
    if not participante_ids:
        return {}
    asistencias = (
        AsistenciaEncuentro.query.options(joinedload(AsistenciaEncuentro.encuentro))
        .join(EncuentroCapacitacion)
        .filter(AsistenciaEncuentro.participante_id.in_(participante_ids))
        .filter(EncuentroCapacitacion.estado != "cancelado")
        .all()
    )
    acrs = Acreditacion.query.filter(Acreditacion.persona_id.in_(participante_ids)).all()
    acr_by_asist = {a.cronograma_persona_id: a for a in acrs if a.cronograma_persona_id}
    acr_by_key = {(a.persona_id, a.programa_id, a.plan_id, a.curso_id): a for a in acrs}
    resultado: dict[int, list] = defaultdict(list)
    for asist in asistencias:
        enc = asist.encuentro
        if not enc:
            continue
        acr = acr_by_asist.get(asist.id)
        if acr is None and enc.curso_id and enc.programa_id and enc.plan_id:
            acr = acr_by_key.get((asist.participante_id, enc.programa_id, enc.plan_id, enc.curso_id))
        resultado[asist.participante_id].append((asist, enc, acr))
    return resultado


def resumen_dashboard(
    empresa_id: int,
    *,
    sector_id: int | None = None,
    participante_ids: list[int] | None = None,
    incluir_todas_personas: bool = False,
) -> dict:
    participantes_q = Participante.query.filter_by(empresa_id=empresa_id, activo=True)
    if sector_id:
        participantes_q = participantes_q.filter_by(sector_id=sector_id)
    if participante_ids is not None:
        if not participante_ids:
            participantes = []
        else:
            participantes_q = participantes_q.filter(Participante.id.in_(participante_ids))
            participantes = participantes_q.all()
    else:
        participantes = participantes_q.all()
    pids = [p.id for p in participantes]

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
    estado_habilitado: dict[int, bool] = {}
    programados = _programados_por_persona([p.id for p in participantes])

    for p in participantes:
        data = analitico_participante(p.id, empresa_id=empresa_id)
        pend = data["resumen"]["total_pendientes"]
        realizados = data["resumen"]["total_cursos_realizados"]
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

        cursos_ok = _cursos_ok_de_analitico(data, hoy)
        habilitada = persona_habilitada_por_programados(programados.get(p.id, []), hoy, cursos_ok)
        estado_habilitado[p.id] = habilitada
        if habilitada:
            verde += 1
        else:
            rojo += 1

        total_req = realizados + pend
        pct_persona = round((realizados / total_req) * 100) if total_req else 100
        cumplimiento_por_persona.append(
            {"id": p.id, "nombre": p.nombre_completo, "pct": pct_persona, "pendientes": pend}
        )

        sid = p.sector_id or 0
        if sid not in cumplimiento_por_sector:
            cumplimiento_por_sector[sid] = {"ok": 0, "total": 0, "nombre": p.sector.nombre if p.sector else "Sin sector"}
        cumplimiento_por_sector[sid]["total"] += 1
        if habilitada:
            cumplimiento_por_sector[sid]["ok"] += 1

    registros_q = (
        RegistroCapacitacion.query.filter_by(empresa_id=empresa_id)
        .filter(RegistroCapacitacion.fecha_realizacion >= inicio_mes)
        .filter(RegistroCapacitacion.fecha_realizacion <= fin_mes)
    )
    if participante_ids is not None:
        registros_q = registros_q.filter(
            RegistroCapacitacion.participante_id.in_(pids or [-1])
        )
    registros_mes = registros_q.all()
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
            if estado_habilitado.get(p.id, True):
                s_v += 1
            else:
                s_r += 1
        if del_sector:
            filas_sector.append({"id": sector.id, "nombre": sector.nombre, "verde": s_v, "rojo": s_r, "gris": s_g})

    certs_q = CertificacionEmpleado.query.filter_by(empresa_id=empresa_id)
    if participante_ids is not None:
        certs_q = certs_q.filter(CertificacionEmpleado.participante_id.in_(pids or [-1]))
    certs_vigentes = (
        certs_q.filter_by(vigente=True)
        .filter(
            (CertificacionEmpleado.fecha_vencimiento.is_(None))
            | (CertificacionEmpleado.fecha_vencimiento >= hoy)
        )
        .count()
    )
    certs_vencidas_count = (
        certs_q.filter(CertificacionEmpleado.fecha_vencimiento.isnot(None))
        .filter(CertificacionEmpleado.fecha_vencimiento < hoy)
        .count()
    )

    evolucion = _evolucion_mensual(
        empresa_id, meses=6, participante_ids=pids if participante_ids is not None else None
    )
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
        "cumplimiento_por_persona": sorted(cumplimiento_por_persona, key=lambda x: x["pct"])[
            : None if incluir_todas_personas else 15
        ],
        "personas_detalle": [
            {
                **item,
                "habilitada": estado_habilitado.get(item["id"], True),
                "legajo": next((p.legajo for p in participantes if p.id == item["id"]), None),
                "puesto": next(
                    (p.puesto.nombre if p.puesto else None for p in participantes if p.id == item["id"]),
                    None,
                ),
            }
            for item in sorted(cumplimiento_por_persona, key=lambda x: x["nombre"].lower())
        ]
        if incluir_todas_personas
        else [],
        "ranking_vencimientos": ranking,
        "evolucion_mensual": evolucion,
        # Habilitados por defecto. Rojo solo si un curso programado se desaprobó
        # o el encuentro se dictó y el mes venció sin aprobar.
        "habilitados_pct": round(verde / total * 100) if participantes else 0,
        "inhabilitados_pct": round(rojo / total * 100) if participantes else 0,
        "totales": {"participantes": len(participantes), "encuentros_mes": encuentros_mes},
    }


def _evolucion_mensual(
    empresa_id: int, meses: int = 6, participante_ids: list[int] | None = None
) -> list[dict]:
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
        q = (
            RegistroCapacitacion.query.filter_by(empresa_id=empresa_id)
            .filter(RegistroCapacitacion.fecha_realizacion >= desde)
            .filter(RegistroCapacitacion.fecha_realizacion <= hasta)
        )
        if participante_ids is not None:
            q = q.filter(RegistroCapacitacion.participante_id.in_(participante_ids or [-1]))
        resultado.append({"mes": f"{y}-{m:02d}", "realizadas": q.count()})
    return resultado


def informe_cliente(empresa_id: int, cliente_id: int) -> dict:
    from gos.modulos.capacitacion.services.cliente_service import (
        cliente_dict,
        ids_participantes_de_cliente,
        obtener_cliente,
    )
    from gos.modulos.capacitacion.services.config_service import obtener_config

    cliente = obtener_cliente(empresa_id, cliente_id)
    pids = ids_participantes_de_cliente(empresa_id, cliente_id)
    data = resumen_dashboard(
        empresa_id,
        participante_ids=pids,
        incluir_todas_personas=True,
    )
    cfg = obtener_config(empresa_id)
    data["cliente"] = cliente_dict(cliente, personas_count=len(pids))
    data["logo_empresa"] = {
        "tiene_logo": bool(cfg.get("tiene_logo_empresa")),
        "url": "/gos/capacitacion/api/configuracion/logo",
        "fallback_url": "/static/img/gos-logo.png",
    }
    data["fecha_informe"] = date.today().isoformat()
    return data


def encuentros_cronograma(empresa_id: int, desde: date, hasta: date) -> list[dict]:
    """Incluye el mes programado (`fecha`) y el día real (`fecha_realizacion`)."""
    rows = (
        EncuentroCapacitacion.query.filter_by(empresa_id=empresa_id)
        .filter(
            or_(
                and_(
                    EncuentroCapacitacion.fecha >= desde,
                    EncuentroCapacitacion.fecha <= hasta,
                ),
                and_(
                    EncuentroCapacitacion.fecha_realizacion.isnot(None),
                    EncuentroCapacitacion.fecha_realizacion >= desde,
                    EncuentroCapacitacion.fecha_realizacion <= hasta,
                ),
            )
        )
        .order_by(EncuentroCapacitacion.fecha, EncuentroCapacitacion.hora_inicio)
        .all()
    )
    return [
        {
            "id": e.id,
            "titulo": e.titulo,
            "fecha": e.fecha.isoformat(),
            "mes": e.fecha.strftime("%Y-%m") if e.fecha else None,
            "fecha_realizacion": e.fecha_realizacion.isoformat() if e.fecha_realizacion else None,
            "hora_inicio": e.hora_inicio.isoformat() if e.hora_inicio else None,
            "hora_fin": e.hora_fin.isoformat() if e.hora_fin else None,
            "lugar": e.lugar,
            "link_virtual": e.link_virtual,
            "instructor": e.instructor,
            "instructor_id": e.instructor_id,
            "origen": e.origen,
            "empresa_capacitadora_id": e.empresa_capacitadora_id,
            "empresa_capacitadora_nombre": e.empresa_capacitadora.nombre if e.empresa_capacitadora else None,
            "estado": e.estado,
            "programa_id": e.programa_id,
            "curso_id": e.curso_id,
            "curso_codigo": e.curso.codigo if e.curso else None,
            "curso_nombre": e.curso.nombre if e.curso else None,
            "inscriptos": e.asistencias.count() if e.asistencias else 0,
        }
        for e in rows
    ]
