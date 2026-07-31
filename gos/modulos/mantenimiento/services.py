"""Consultas del plan de mantenimiento y VTV."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from gos.modulos.mantenimiento.models import (
    MantPlanCelda,
    MantPlanMeta,
    MantReporteOrden,
    MantReporteSolicitud,
    MantReporteTarea,
    MantSectorPersona,
    MantUnidad,
    MantVtv,
    MantVtvTurno,
)

MESES_LABEL = [
    "",
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
]

VTV_ALERTA_DIAS = 30
VTV_DIAS_HABILES = {1, 3}  # martes=1, jueves=3 (Monday=0)
VTV_RESULTADOS = ("apto", "condicional", "rechazada")
VTV_BAJA_DIAS_ANTES = 2


def _fin_de_mes(anio: int, mes: int) -> date:
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def _persona_activa_al(persona: MantSectorPersona, al: date) -> bool:
    """Activo al cierre del período: alta <= al y (sin baja o baja después de al)."""
    if persona.fecha_alta is None or persona.fecha_alta > al:
        return False
    if persona.fecha_baja is None:
        return True
    return persona.fecha_baja > al


def _personal_sector_al(personas: list[MantSectorPersona], al: date) -> int:
    return sum(1 for p in personas if _persona_activa_al(p, al))


_ROLES_NO_OPERATIVOS = frozenset({"GERENTE", "COORDINADOR"})


def _es_operativo(persona: MantSectorPersona) -> bool:
    """Operativo = todo el personal activo salvo gerente y coordinador."""
    rol = (persona.funcion_general or persona.funcion or "").strip().upper()
    return rol not in _ROLES_NO_OPERATIVOS


def _personal_operativo_al(personas: list[MantSectorPersona], al: date) -> int:
    return sum(
        1 for p in personas if _persona_activa_al(p, al) and _es_operativo(p)
    )


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, month=2, day=28)


def es_dia_vtv(d: date) -> bool:
    return d.weekday() in VTV_DIAS_HABILES


def fecha_baja_para(fecha_vtv: date) -> date:
    return fecha_vtv - timedelta(days=VTV_BAJA_DIAS_ANTES)


def fechas_vtv_disponibles(
    desde: date | None = None,
    cantidad: int = 24,
    hasta: date | None = None,
) -> list[dict]:
    """Próximos martes y jueves para programar VTV."""
    desde = desde or date.today()
    cursor = desde
    out = []
    dias_semana = {0: "lun", 1: "mar", 2: "mié", 3: "jue", 4: "vie", 5: "sáb", 6: "dom"}
    while len(out) < cantidad:
        if hasta and cursor > hasta:
            break
        if es_dia_vtv(cursor):
            baja = fecha_baja_para(cursor)
            out.append(
                {
                    "fecha": cursor.isoformat(),
                    "label": f"{dias_semana[cursor.weekday()]} {cursor.strftime('%d/%m/%Y')}",
                    "fecha_baja": baja.isoformat(),
                    "weekday": cursor.weekday(),
                }
            )
        cursor += timedelta(days=1)
        if (cursor - desde).days > 400:
            break
    return out


def _turno_dict(t: MantVtvTurno) -> dict:
    return {
        "id": t.id,
        "unidad_id": t.unidad_id,
        "codigo": t.unidad.codigo if t.unidad else None,
        "nombre": t.unidad.nombre if t.unidad else None,
        "fecha_vtv": t.fecha_vtv.isoformat(),
        "fecha_baja": t.fecha_baja.isoformat(),
        "estado": t.estado,
        "resultado": t.resultado,
        "fecha_realizada": t.fecha_realizada.isoformat() if t.fecha_realizada else None,
        "tiene_certificado": bool(t.certificado_path),
        "certificado_nombre": t.certificado_nombre,
        "observaciones": t.observaciones,
    }


def get_vtv(session: Session, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    alerta = hoy + timedelta(days=VTV_ALERTA_DIAS)

    rows = session.execute(
        select(MantVtv)
        .options(joinedload(MantVtv.unidad))
        .join(MantUnidad)
        .order_by(MantVtv.vencimiento, MantUnidad.nombre)
    ).scalars().all()

    turnos_prog = session.execute(
        select(MantVtvTurno)
        .where(MantVtvTurno.estado == "programada")
        .options(joinedload(MantVtvTurno.unidad))
    ).scalars().all()
    turno_por_unidad = {t.unidad_id: t for t in turnos_prog}

    items = []
    vencidas = 0
    por_vencer = 0
    vigentes = 0
    bloqueadas = 0
    programadas = 0
    en_baja = 0

    for v in rows:
        dias = (v.vencimiento - hoy).days
        turno = turno_por_unidad.get(v.unidad_id)
        en_prep = bool(
            turno
            and turno.fecha_baja <= hoy <= turno.fecha_vtv
        )

        if v.bloqueado:
            estado = "bloqueada"
            bloqueadas += 1
        elif dias < 0:
            estado = "vencida"
            vencidas += 1
        elif v.vencimiento <= alerta:
            estado = "por_vencer"
            por_vencer += 1
        else:
            estado = "vigente"
            vigentes += 1

        if turno:
            programadas += 1
        if en_prep:
            en_baja += 1

        items.append(
            {
                "unidad_id": v.unidad_id,
                "codigo": v.unidad.codigo,
                "nombre": v.unidad.nombre,
                "vencimiento": v.vencimiento.isoformat(),
                "dias": dias,
                "estado": estado,
                "bloqueado": bool(v.bloqueado),
                "resultado_ultimo": v.resultado_ultimo,
                "en_baja": en_prep,
                "turno": _turno_dict(turno) if turno else None,
            }
        )

    agenda = sorted(
        [_turno_dict(t) for t in turnos_prog],
        key=lambda x: x["fecha_vtv"],
    )

    historial = session.execute(
        select(MantVtvTurno)
        .where(MantVtvTurno.estado == "realizada")
        .options(joinedload(MantVtvTurno.unidad))
        .order_by(MantVtvTurno.fecha_realizada.desc(), MantVtvTurno.id.desc())
        .limit(40)
    ).scalars().all()

    return {
        "hoy": hoy.isoformat(),
        "alerta_dias": VTV_ALERTA_DIAS,
        "reglas": {
            "dias_vtv": ["martes", "jueves"],
            "baja_dias_antes": VTV_BAJA_DIAS_ANTES,
            "condicional_dias": 30,
            "apto_renueva_anios": 1,
        },
        "fechas_disponibles": fechas_vtv_disponibles(hoy, cantidad=20),
        "kpis": {
            "total": len(items),
            "vencidas": vencidas,
            "por_vencer": por_vencer,
            "vigentes": vigentes,
            "bloqueadas": bloqueadas,
            "programadas": programadas,
            "en_baja": en_baja,
        },
        "items": items,
        "agenda": agenda,
        "historial": [_turno_dict(t) for t in historial],
    }


def programar_vtv(
    session: Session,
    unidad_id: int,
    fecha_vtv: date,
    observaciones: str | None = None,
) -> dict:
    if not es_dia_vtv(fecha_vtv):
        raise ValueError("Las VTV solo se pueden programar martes o jueves.")

    unidad = session.get(MantUnidad, unidad_id)
    if not unidad or not unidad.activo:
        raise ValueError("Unidad no encontrada.")

    vtv = session.execute(
        select(MantVtv).where(MantVtv.unidad_id == unidad_id)
    ).scalar_one_or_none()
    if not vtv:
        raise ValueError("La unidad no tiene vencimiento VTV cargado. Importá el Excel primero.")

    existente = session.execute(
        select(MantVtvTurno).where(
            MantVtvTurno.unidad_id == unidad_id,
            MantVtvTurno.estado == "programada",
        )
    ).scalar_one_or_none()
    if existente:
        raise ValueError(
            f"Ya hay un turno programado para {unidad.nombre} "
            f"el {existente.fecha_vtv.strftime('%d/%m/%Y')}."
        )

    turno = MantVtvTurno(
        unidad_id=unidad_id,
        fecha_vtv=fecha_vtv,
        fecha_baja=fecha_baja_para(fecha_vtv),
        estado="programada",
        observaciones=(observaciones or "").strip() or None,
    )
    session.add(turno)
    session.commit()
    session.refresh(turno)
    turno.unidad = unidad
    return _turno_dict(turno)


def cancelar_turno(session: Session, turno_id: int) -> dict:
    turno = session.execute(
        select(MantVtvTurno)
        .where(MantVtvTurno.id == turno_id)
        .options(joinedload(MantVtvTurno.unidad))
    ).scalar_one_or_none()
    if not turno:
        raise ValueError("Turno no encontrado.")
    if turno.estado != "programada":
        raise ValueError("Solo se pueden cancelar turnos programados.")
    turno.estado = "cancelada"
    session.commit()
    return _turno_dict(turno)


def registrar_resultado_vtv(
    session: Session,
    turno_id: int,
    resultado: str,
    fecha_realizada: date | None = None,
    observaciones: str | None = None,
    file_storage=None,
) -> dict:
    resultado = (resultado or "").strip().lower()
    if resultado not in VTV_RESULTADOS:
        raise ValueError("Resultado inválido. Usá: apto, condicional o rechazada.")

    turno = session.execute(
        select(MantVtvTurno)
        .where(MantVtvTurno.id == turno_id)
        .options(joinedload(MantVtvTurno.unidad))
    ).scalar_one_or_none()
    if not turno:
        raise ValueError("Turno no encontrado.")
    if turno.estado != "programada":
        raise ValueError("El turno no está programado.")

    vtv = session.execute(
        select(MantVtv).where(MantVtv.unidad_id == turno.unidad_id)
    ).scalar_one_or_none()
    if not vtv:
        raise ValueError("No hay registro VTV de la unidad.")

    hecha = fecha_realizada or turno.fecha_vtv
    turno.estado = "realizada"
    turno.resultado = resultado
    turno.fecha_realizada = hecha
    if observaciones is not None:
        turno.observaciones = observaciones.strip() or None

    if file_storage and getattr(file_storage, "filename", None):
        from gos.modulos.mantenimiento.storage import borrar_certificado, guardar_certificado

        session.flush()
        if turno.certificado_path:
            borrar_certificado(turno.certificado_path)
        path, nombre = guardar_certificado(turno.id, file_storage)
        turno.certificado_path = path
        turno.certificado_nombre = nombre

    vtv.resultado_ultimo = resultado
    if resultado == "apto":
        vtv.vencimiento = _add_years(hecha, 1)
        vtv.bloqueado = False
    elif resultado == "condicional":
        # 30 días para volver a verificar; hay que reprogramar
        vtv.vencimiento = hecha + timedelta(days=30)
        vtv.bloqueado = False
    else:  # rechazada
        vtv.bloqueado = True

    session.commit()
    session.refresh(turno)
    return {
        "turno": _turno_dict(turno),
        "vencimiento": vtv.vencimiento.isoformat(),
        "bloqueado": bool(vtv.bloqueado),
        "resultado": resultado,
    }


def adjuntar_certificado(session: Session, turno_id: int, file_storage) -> dict:
    from gos.modulos.mantenimiento.storage import borrar_certificado, guardar_certificado

    turno = session.execute(
        select(MantVtvTurno)
        .where(MantVtvTurno.id == turno_id)
        .options(joinedload(MantVtvTurno.unidad))
    ).scalar_one_or_none()
    if not turno:
        raise ValueError("Turno no encontrado.")
    if turno.certificado_path:
        borrar_certificado(turno.certificado_path)
    path, nombre = guardar_certificado(turno.id, file_storage)
    turno.certificado_path = path
    turno.certificado_nombre = nombre
    session.commit()
    return _turno_dict(turno)


def obtener_certificado(session: Session, turno_id: int) -> tuple:
    from pathlib import Path

    turno = session.get(MantVtvTurno, turno_id)
    if not turno or not turno.certificado_path:
        raise ValueError("Certificado no encontrado.")
    path = Path(turno.certificado_path)
    if not path.is_file():
        raise ValueError("Archivo no disponible.")
    return path, turno.certificado_nombre or path.name


def get_meta(session: Session) -> dict:
    anios = sorted(
        {
            row[0]
            for row in session.execute(select(MantPlanCelda.anio).distinct()).all()
            if row[0]
        },
        reverse=True,
    )
    metas = {
        m.anio: {
            "anio": m.anio,
            "titulo": m.titulo,
            "sector": m.sector,
            "observaciones": m.observaciones,
        }
        for m in session.execute(select(MantPlanMeta)).scalars()
    }
    unidades = [
        {"id": u.id, "codigo": u.codigo, "nombre": u.nombre}
        for u in session.execute(
            select(MantUnidad).where(MantUnidad.activo.is_(True)).order_by(MantUnidad.nombre)
        ).scalars()
    ]
    return {"anios": anios, "metas": metas, "unidades": unidades}


def _cumplimiento(p: float, e: float) -> float | None:
    if p <= 0:
        return None
    return round(e / p, 4)


def _mes_corte_cumplimiento(anio: int, hoy: date) -> int:
    """Último mes que entra en C: solo meses ya alcanzados según la fecha actual.

    - Año pasado → 12 (todo el año)
    - Año futuro → 0 (nada entra todavía)
    - Año actual → mes de hoy (inclusive)
    """
    if anio < hoy.year:
        return 12
    if anio > hoy.year:
        return 0
    return hoy.month


def get_plan(session: Session, anio: int | None = None, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    anios = sorted(
        {
            row[0]
            for row in session.execute(select(MantPlanCelda.anio).distinct()).all()
            if row[0]
        },
        reverse=True,
    )
    if anio is None:
        anio = anios[0] if anios else hoy.year

    mes_corte = _mes_corte_cumplimiento(anio, hoy)

    meta = session.execute(
        select(MantPlanMeta).where(MantPlanMeta.anio == anio)
    ).scalar_one_or_none()

    celdas = session.execute(
        select(MantPlanCelda)
        .where(MantPlanCelda.anio == anio)
        .options(joinedload(MantPlanCelda.unidad))
    ).scalars().all()

    by_unidad: dict[int, dict] = {}
    tipos_count = {1: 0, 2: 0, 3: 0, 4: 0}
    for cel in celdas:
        u = cel.unidad
        if u.id not in by_unidad:
            by_unidad[u.id] = {
                "id": u.id,
                "codigo": u.codigo,
                "nombre": u.nombre,
                "meses": {m: {"r": 0, "p": 0, "e": 0} for m in range(1, 13)},
                "tot_p": 0.0,
                "tot_e": 0.0,
            }
        row = by_unidad[u.id]
        row["meses"][cel.mes] = {"r": cel.r, "p": cel.p, "e": cel.e}
        # P/E/C solo acumulan meses ya alcanzados (fecha actual)
        if cel.mes <= mes_corte:
            row["tot_p"] += cel.p or 0
            row["tot_e"] += cel.e or 0
        tipo = int(cel.r) if cel.r and float(cel.r) == int(cel.r) else None
        if tipo in tipos_count:
            tipos_count[tipo] += 1

    # Incluir unidades con VTV aunque no tengan plan ese año
    unidades_ids = set(by_unidad)
    for u in session.execute(
        select(MantUnidad).where(MantUnidad.activo.is_(True)).order_by(MantUnidad.nombre)
    ).scalars():
        if u.id not in unidades_ids:
            by_unidad[u.id] = {
                "id": u.id,
                "codigo": u.codigo,
                "nombre": u.nombre,
                "meses": {m: {"r": 0, "p": 0, "e": 0} for m in range(1, 13)},
                "tot_p": 0.0,
                "tot_e": 0.0,
            }

    filas = []
    for row in sorted(by_unidad.values(), key=lambda x: x["nombre"]):
        row["cumplimiento"] = _cumplimiento(row["tot_p"], row["tot_e"])
        # serializar meses como lista indexada 1..12 para JSON estable
        row["meses"] = [row["meses"][m] for m in range(1, 13)]
        filas.append(row)

    tot_p = sum(f["tot_p"] for f in filas)
    tot_e = sum(f["tot_e"] for f in filas)

    por_mes = []
    for m in range(1, 13):
        mp = sum(f["meses"][m - 1]["p"] for f in filas)
        me = sum(f["meses"][m - 1]["e"] for f in filas)
        cuenta = m <= mes_corte
        por_mes.append(
            {
                "mes": m,
                "label": MESES_LABEL[m],
                "p": mp,
                "e": me,
                "cuenta_en_c": cuenta,
                "cumplimiento": _cumplimiento(mp, me) if cuenta else None,
            }
        )

    return {
        "anio": anio,
        "anios": anios,
        "hoy": hoy.isoformat(),
        "mes_corte": mes_corte,
        "meta": {
            "titulo": meta.titulo if meta else None,
            "sector": meta.sector if meta else None,
            "observaciones": meta.observaciones if meta else None,
        },
        "kpis": {
            "unidades": len(filas),
            "programado": tot_p,
            "ejecutado": tot_e,
            "cumplimiento": _cumplimiento(tot_p, tot_e),
            "por_tipo": tipos_count,
        },
        "por_mes": por_mes,
        "filas": filas,
        "leyenda": {
            "r": "Referencia (tipo de mantenimiento 1–4)",
            "p": "Programado (mes en que se programó)",
            "e": "Ejecutado (mes en que se realizó)",
            "c": "Cumplimiento (E/P) solo con meses ya alcanzados a la fecha",
        },
    }


def _agg_count(items: list, key_fn) -> list[dict]:
    counts: dict[str, int] = {}
    for item in items:
        key = (key_fn(item) or "Sin dato").strip() or "Sin dato"
        counts[key] = counts.get(key, 0) + 1
    return [
        {"label": label, "valor": valor}
        for label, valor in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]


def _agg_sum(items: list, key_fn, value_fn) -> list[dict]:
    totals: dict[str, float] = {}
    for item in items:
        key = (key_fn(item) or "Sin dato").strip() or "Sin dato"
        totals[key] = totals.get(key, 0.0) + float(value_fn(item) or 0)
    return [
        {"label": label, "valor": round(valor, 2)}
        for label, valor in sorted(totals.items(), key=lambda x: (-x[1], x[0]))
    ]


def _ordenes_por_tipo(tareas: list, total_ordenes: int) -> list[dict]:
    """Órdenes distintas por tipo + % sobre el total de órdenes del período."""
    por_tipo: dict[str, set[str]] = {}
    for t in tareas:
        tipo = (t.tipo or "Sin dato").strip() or "Sin dato"
        nro = (t.nro_orden or "").strip()
        if not nro:
            continue
        por_tipo.setdefault(tipo, set()).add(nro)
    total = total_ordenes or 0
    filas = []
    for label, nros in por_tipo.items():
        cantidad = len(nros)
        filas.append(
            {
                "label": label,
                "cantidad": cantidad,
                "pct": round(cantidad / total, 4) if total else 0.0,
            }
        )
    return sorted(filas, key=lambda x: (-x["cantidad"], x["label"]))


def get_reporte_mensual(
    session: Session,
    anio: int | None = None,
    trimestre: int | None = None,
    todos: bool = False,
) -> dict:
    """Dashboard tipo Power BI «Reporte Mensual»: órdenes + horas + solicitudes.

    Con todos=True compara año a año (sin filtro de año). Con un año, serie mes a mes.
    """
    anios = sorted(
        {
            row[0]
            for row in session.execute(select(MantReporteOrden.anio).distinct()).all()
            if row[0]
        }
        | {
            row[0]
            for row in session.execute(select(MantReporteTarea.anio).distinct()).all()
            if row[0]
        }
        | {
            row[0]
            for row in session.execute(select(MantReporteSolicitud.anio).distinct()).all()
            if row[0]
        },
        reverse=True,
    )
    if todos:
        anio = None
        trimestre = None
    elif anio is None:
        anio = anios[0] if anios else date.today().year
    if trimestre is not None and trimestre not in (1, 2, 3, 4):
        trimestre = None

    ordenes_q = select(MantReporteOrden)
    tareas_q = select(MantReporteTarea)
    solicitudes_q = select(MantReporteSolicitud)
    if anio is not None:
        ordenes_q = ordenes_q.where(MantReporteOrden.anio == anio)
        tareas_q = tareas_q.where(MantReporteTarea.anio == anio)
        solicitudes_q = solicitudes_q.where(MantReporteSolicitud.anio == anio)
    if trimestre:
        ordenes_q = ordenes_q.where(MantReporteOrden.trimestre == trimestre)
        tareas_q = tareas_q.where(MantReporteTarea.trimestre == trimestre)
        solicitudes_q = solicitudes_q.where(MantReporteSolicitud.trimestre == trimestre)

    ordenes = list(session.execute(ordenes_q).scalars())
    tareas = list(session.execute(tareas_q).scalars())
    solicitudes = list(session.execute(solicitudes_q).scalars())
    sector_personas = list(session.execute(select(MantSectorPersona)).scalars())

    estados = sorted({(o.estado or "Sin estado").strip() or "Sin estado" for o in ordenes})
    vista = "anual" if todos else "mensual"

    if todos:
        anios_asc = sorted(anios)
        ordenes_por_mes = []
        solicitudes_por_mes = []
        gente_ordenes_por_mes = []
        for y in anios_asc:
            fila = {"mes": None, "anio": y, "label": str(y), "total": 0, "por_estado": {}}
            for estado in estados:
                fila["por_estado"][estado] = 0
            for o in ordenes:
                if o.anio != y:
                    continue
                estado = (o.estado or "Sin estado").strip() or "Sin estado"
                fila["total"] += 1
                fila["por_estado"][estado] = fila["por_estado"].get(estado, 0) + 1
            ordenes_por_mes.append(fila)

            solicitudes_por_mes.append(
                {
                    "mes": None,
                    "anio": y,
                    "label": str(y),
                    "total": sum(1 for s in solicitudes if s.anio == y),
                }
            )
            corte = _fin_de_mes(y, 12)
            personal = _personal_sector_al(sector_personas, corte)
            personal_operativo = _personal_operativo_al(sector_personas, corte)
            ordenes_y = sum(1 for o in ordenes if o.anio == y)
            personas_por_orden = (
                round(personal_operativo / ordenes_y, 2) if ordenes_y else None
            )
            gente_ordenes_por_mes.append(
                {
                    "mes": None,
                    "anio": y,
                    "label": str(y),
                    "personal": personal,
                    "personal_operativo": personal_operativo,
                    "ordenes": ordenes_y,
                    "personas_por_orden": personas_por_orden,
                }
            )
        corte_personal = (
            _fin_de_mes(anios_asc[-1], 12) if anios_asc else date.today()
        )
    else:
        meses_rango = (
            list(range((trimestre - 1) * 3 + 1, trimestre * 3 + 1))
            if trimestre
            else list(range(1, 13))
        )
        ordenes_por_mes = []
        for mes in meses_rango:
            fila = {"mes": mes, "label": MESES_LABEL[mes], "total": 0, "por_estado": {}}
            for estado in estados:
                fila["por_estado"][estado] = 0
            for o in ordenes:
                if o.mes != mes:
                    continue
                estado = (o.estado or "Sin estado").strip() or "Sin estado"
                fila["total"] += 1
                fila["por_estado"][estado] = fila["por_estado"].get(estado, 0) + 1
            ordenes_por_mes.append(fila)

        solicitudes_por_mes = []
        gente_ordenes_por_mes = []
        for mes in meses_rango:
            total = sum(1 for s in solicitudes if s.mes == mes)
            solicitudes_por_mes.append(
                {"mes": mes, "label": MESES_LABEL[mes], "total": total}
            )
            corte = _fin_de_mes(anio, mes)
            personal = _personal_sector_al(sector_personas, corte)
            personal_operativo = _personal_operativo_al(sector_personas, corte)
            ordenes_mes = sum(1 for o in ordenes if o.mes == mes)
            personas_por_orden = (
                round(personal_operativo / ordenes_mes, 2) if ordenes_mes else None
            )
            gente_ordenes_por_mes.append(
                {
                    "mes": mes,
                    "label": MESES_LABEL[mes],
                    "personal": personal,
                    "personal_operativo": personal_operativo,
                    "ordenes": ordenes_mes,
                    "personas_por_orden": personas_por_orden,
                }
            )
        corte_personal = (
            _fin_de_mes(anio, meses_rango[-1]) if meses_rango else date.today()
        )

    horas_totales = round(sum(float(t.total_horas or 0) for t in tareas), 2)
    solicitudes_por_estado = _agg_count(solicitudes, lambda s: s.estado)

    personal_kpi = (
        gente_ordenes_por_mes[-1]["personal"] if gente_ordenes_por_mes else 0
    )
    personal_activos = sorted(
        [
            {
                "legajo": p.legajo,
                "nombre": p.nombre,
                "fecha_alta": p.fecha_alta.isoformat() if p.fecha_alta else None,
                "fecha_baja": p.fecha_baja.isoformat() if p.fecha_baja else None,
                "localidad_real": p.localidad_real,
                "funcion_general": p.funcion_general,
                "funcion": p.funcion,
                "grupo": p.grupo,
                "turno": p.turno,
            }
            for p in sector_personas
            if _persona_activa_al(p, corte_personal)
        ],
        key=lambda x: (x.get("nombre") or "").lower(),
    )
    activos_objs = [p for p in sector_personas if _persona_activa_al(p, corte_personal)]
    personal_por_funcion = _agg_count(
        activos_objs, lambda p: p.funcion or p.funcion_general
    )
    personal_por_localidad = _agg_count(activos_objs, lambda p: p.localidad_real)

    return {
        "anio": anio,
        "anios": anios,
        "todos": todos,
        "vista": vista,
        "trimestre": trimestre,
        "tiene_datos": bool(anios),
        "kpis": {
            "ordenes": len(ordenes),
            "horas": horas_totales,
            "personal": personal_kpi,
            "unidades_con_orden": len({(o.unidad or "").strip() for o in ordenes if (o.unidad or "").strip()}),
            "tareas": len(tareas),
            "solicitudes": len(solicitudes),
        },
        "horas_por_clase": _agg_sum(tareas, lambda t: t.clase, lambda t: t.total_horas),
        "horas_por_tipo": _agg_sum(tareas, lambda t: t.tipo, lambda t: t.total_horas),
        "horas_por_lugar": _agg_sum(tareas, lambda t: t.lugar, lambda t: t.total_horas),
        "tareas_por_clase": _agg_count(tareas, lambda t: t.clase),
        "tareas_por_tipo": _agg_count(tareas, lambda t: t.tipo),
        "ordenes_por_tipo": _ordenes_por_tipo(tareas, len(ordenes)),
        "ordenes_por_mes": ordenes_por_mes,
        "ordenes_por_estado": _agg_count(ordenes, lambda o: o.estado),
        "gente_ordenes_por_mes": gente_ordenes_por_mes,
        "personal_activos": personal_activos,
        "personal_por_funcion": personal_por_funcion,
        "personal_por_localidad": personal_por_localidad,
        "estados": estados,
        "equipos_demanda": _agg_count(ordenes, lambda o: o.unidad)[:20],
        "horas_por_unidad": _agg_sum(tareas, lambda t: t.unidad, lambda t: t.total_horas)[:20],
        "solicitudes_por_estado": solicitudes_por_estado,
        "solicitudes_por_mes": solicitudes_por_mes,
    }
