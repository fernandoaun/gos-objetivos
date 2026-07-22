from __future__ import annotations

from typing import Optional

from sqlalchemy import extract, func, select, union
from sqlalchemy.orm import Session

from gos.modulos.vacaciones.models import Registro, TotHs, Vacacion


def get_anios(db: Session) -> list[int]:
    q_reg = select(extract("year", Registro.fecha).label("anio")).where(
        Registro.fecha.isnot(None)
    )
    q_vac = select(Vacacion.anio.label("anio")).where(Vacacion.anio.isnot(None))
    subq = union(q_reg, q_vac).subquery()
    rows = db.execute(select(subq.c.anio).order_by(subq.c.anio)).scalars().all()
    return [int(r) for r in rows if r is not None]


def get_sectores(db: Session) -> list[str]:
    q_reg = select(Registro.sector.label("sector")).where(
        Registro.sector.isnot(None), Registro.sector != "SIN DATO"
    )
    q_vac = select(Vacacion.sector.label("sector")).where(
        Vacacion.sector.isnot(None), Vacacion.sector != "SIN DATO"
    )
    subq = union(q_reg, q_vac).subquery()
    rows = db.execute(select(subq.c.sector).order_by(subq.c.sector)).scalars().all()
    return [r for r in rows if r]


def get_empleados(db: Session, sector: Optional[str] = None) -> list[str]:
    q_reg = select(Registro.empleado.label("empleado")).where(Registro.empleado.isnot(None))
    q_vac = select(Vacacion.empleado.label("empleado")).where(Vacacion.empleado.isnot(None))
    if sector:
        q_reg = q_reg.where(Registro.sector == sector)
        q_vac = q_vac.where(Vacacion.sector == sector)
    subq = union(q_reg, q_vac).subquery()
    return list(db.execute(select(subq.c.empleado).order_by(subq.c.empleado)).scalars().all())


def _resolve_anios(
    anios: Optional[list[int]] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
) -> Optional[list[int]]:
    if anios:
        return sorted({int(a) for a in anios})
    year_desde = int(desde[:4]) if desde else None
    year_hasta = int(hasta[:4]) if hasta else None
    if year_desde is None and year_hasta is None:
        return None
    if year_desde is not None and year_hasta is not None:
        return list(range(year_desde, year_hasta + 1))
    if year_desde is not None:
        return [year_desde]
    return [year_hasta] if year_hasta is not None else None


def get_deuda_vacaciones(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sector: Optional[str] = None,
    anios: Optional[list[int]] = None,
) -> list[dict]:
    years = _resolve_anios(anios, desde, hasta)

    q_planilla = select(
        Vacacion.legajo,
        Vacacion.empleado,
        Vacacion.fecha_ingreso,
        Vacacion.sector,
        Vacacion.anio,
        Vacacion.dias_disponibles,
        Vacacion.dias_tomados,
        Vacacion.dias_pendientes,
        Vacacion.comentario,
        Vacacion.nota_q,
        Vacacion.nota_r,
    )
    if years:
        q_planilla = q_planilla.where(Vacacion.anio.in_(years))
    if sector:
        q_planilla = q_planilla.where(Vacacion.sector == sector)
    q_planilla = q_planilla.order_by(Vacacion.empleado, Vacacion.anio)
    planilla_rows = db.execute(q_planilla).all()

    q_real = select(
        Registro.empleado,
        extract("year", Registro.fecha).label("anio_r"),
        func.sum(Registro.vacaciones).label("dias_reales"),
    )
    if years:
        q_real = q_real.where(extract("year", Registro.fecha).in_(years))
    elif desde:
        q_real = q_real.where(Registro.fecha >= desde)
        if hasta:
            q_real = q_real.where(Registro.fecha <= hasta)
    elif hasta:
        q_real = q_real.where(Registro.fecha <= hasta)
    q_real = q_real.group_by(Registro.empleado, extract("year", Registro.fecha))
    real_rows = db.execute(q_real).all()
    reales = {(r.empleado, int(r.anio_r)): r.dias_reales for r in real_rows if r.anio_r}

    result = []
    for row in planilla_rows:
        (
            legajo,
            empleado,
            fecha_ingreso,
            sect,
            anio_val,
            disponibles,
            tomados_planilla,
            _pendientes_excel,
            comentario,
            nota_q,
            nota_r,
        ) = row
        tomados_real = reales.get((empleado, anio_val), 0)
        disp = disponibles or 0
        tom = tomados_planilla or 0
        # Pendientes = disponibles − tomados (no confiar en la columna del Excel).
        pend = disp - tom
        diferencia = tom - (tomados_real or 0)
        result.append(
            {
                "legajo": legajo,
                "empleado": empleado,
                "fecha_ingreso": fecha_ingreso.isoformat() if fecha_ingreso else None,
                "sector": sect,
                "anio": anio_val,
                "dias_disponibles": disp,
                "tomados_planilla": tom,
                "tomados_real": int(tomados_real or 0),
                "dias_pendientes": pend,
                "diferencia": diferencia,
                "comentario": comentario or None,
                "nota_q": nota_q or None,
                "nota_r": nota_r or None,
            }
        )
    return result


def get_resumen_sector(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    anios: Optional[list[int]] = None,
) -> list[dict]:
    years = _resolve_anios(anios, desde, hasta)

    q = select(
        Vacacion.sector,
        func.sum(Vacacion.dias_disponibles),
        func.sum(Vacacion.dias_tomados),
        func.count(func.distinct(Vacacion.empleado)),
    ).where(Vacacion.sector.isnot(None))
    if years:
        q = q.where(Vacacion.anio.in_(years))
    q = q.group_by(Vacacion.sector)
    rows = db.execute(q).all()
    result = []
    for sector, disponibles, tomados, personas in rows:
        personas_n = int(personas or 0)
        disp_n = disponibles or 0
        tom_n = tomados or 0
        pendientes_n = disp_n - tom_n
        result.append(
            {
                "sector": sector,
                "disponibles": disp_n,
                "tomados": tom_n,
                "pendientes": pendientes_n,
                "personas": personas_n,
                "pendientes_por_persona": round(pendientes_n / personas_n, 1) if personas_n else 0,
            }
        )
    result.sort(key=lambda r: r["pendientes"], reverse=True)
    return result


def _parse_period_key(periodo: Optional[str]) -> Optional[tuple[str, str]]:
    """'YYYY-MM-DD|YYYY-MM-DD' → (desde, hasta)."""
    if not periodo or "|" not in periodo:
        return None
    a, b = periodo.split("|", 1)
    a, b = a.strip(), b.strip()
    if len(a) >= 10 and len(b) >= 10:
        return a[:10], b[:10]
    return None


def _tot_hs_filters(
    periodo: Optional[str] = None,
    cliente: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    empleado: Optional[str] = None,
):
    clauses = []
    key = _parse_period_key(periodo)
    if key:
        clauses.append(TotHs.periodo_desde == key[0])
        clauses.append(TotHs.periodo_hasta == key[1])
    if cliente:
        clauses.append(TotHs.cliente == cliente)
    if tipo_servicio:
        clauses.append(TotHs.tipo_servicio == tipo_servicio)
    if empleado:
        clauses.append(TotHs.empleado == empleado)
    return clauses


def get_tot_hs_meta(db: Session) -> dict:
    """Períodos cargados y totales globales."""
    periodos_rows = db.execute(
        select(TotHs.periodo_desde, TotHs.periodo_hasta)
        .distinct()
        .order_by(TotHs.periodo_desde.desc(), TotHs.periodo_hasta.desc())
    ).all()
    periodos = []
    for d, h in periodos_rows:
        periodos.append(
            {
                "desde": d.isoformat(),
                "hasta": h.isoformat(),
                "key": f"{d.isoformat()}|{h.isoformat()}",
                "label": f"{d.strftime('%d/%m/%Y')} al {h.strftime('%d/%m/%Y')}",
            }
        )

    row = db.execute(
        select(
            func.count(TotHs.id),
            func.count(func.distinct(TotHs.empleado)),
            func.min(TotHs.periodo_desde),
            func.max(TotHs.periodo_hasta),
        )
    ).one()
    total, personas, fmin, fmax = row

    clientes = list(
        db.execute(
            select(TotHs.cliente)
            .where(TotHs.cliente.isnot(None), TotHs.cliente != "")
            .distinct()
            .order_by(TotHs.cliente)
        ).scalars().all()
    )
    tipos = list(
        db.execute(
            select(TotHs.tipo_servicio)
            .where(TotHs.tipo_servicio.isnot(None), TotHs.tipo_servicio != "")
            .distinct()
            .order_by(TotHs.tipo_servicio)
        ).scalars().all()
    )
    return {
        "periodos": periodos,
        "fecha_min": fmin.isoformat() if fmin else None,
        "fecha_max": fmax.isoformat() if fmax else None,
        "total_registros": int(total or 0),
        "personas": int(personas or 0),
        "clientes": clientes,
        "tipos_servicio": tipos,
        "anios": sorted({int(p["desde"][:4]) for p in periodos} | {int(p["hasta"][:4]) for p in periodos}),
    }


def get_tot_hs_resumen(
    db: Session,
    periodo: Optional[str] = None,
    cliente: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    **_ignored,
) -> dict:
    clauses = _tot_hs_filters(periodo, cliente, tipo_servicio)
    q = select(
        func.count(TotHs.id),
        func.count(func.distinct(TotHs.empleado)),
        func.min(TotHs.periodo_desde),
        func.max(TotHs.periodo_hasta),
        func.coalesce(func.sum(TotHs.total_horas), 0),
        func.coalesce(func.sum(TotHs.hs_viaje), 0),
        func.coalesce(func.sum(TotHs.hs50), 0),
        func.coalesce(func.sum(TotHs.hs_noc), 0),
        func.coalesce(func.sum(TotHs.hs_noc50), 0),
        func.coalesce(func.sum(TotHs.hs100), 0),
        func.coalesce(func.sum(TotHs.total_hs_viaje), 0),
        func.coalesce(func.sum(TotHs.ausente), 0),
        func.coalesce(func.sum(TotHs.enfermedad), 0),
        func.coalesce(func.sum(TotHs.vacaciones), 0),
        func.coalesce(func.sum(TotHs.licencia), 0),
        func.coalesce(func.sum(TotHs.feriados), 0),
        func.coalesce(func.sum(TotHs.accidente), 0),
        func.coalesce(func.sum(TotHs.francos_comp), 0),
        func.coalesce(func.sum(TotHs.d_normales), 0),
        func.coalesce(func.sum(TotHs.viandas), 0),
        func.coalesce(func.sum(TotHs.traslado), 0),
        func.coalesce(func.sum(TotHs.v_desayuno), 0),
        func.coalesce(func.sum(TotHs.fr_trabajados), 0),
    )
    for c in clauses:
        q = q.where(c)
    row = db.execute(q).one()
    (
        registros, personas, fmin, fmax,
        total_horas, hs_viaje, hs50, hs_noc, hs_noc50, hs100, total_hs_viaje,
        ausente, enfermedad, vacaciones, licencia, feriados,
        accidente, francos_comp, d_normales, viandas, traslado, desayunos, fr_trab,
    ) = row
    extras = float(hs50 or 0) + float(hs100 or 0) + float(hs_noc or 0) + float(hs_noc50 or 0)
    return {
        "registros": int(registros or 0),
        "personas": int(personas or 0),
        "fecha_min": fmin.isoformat() if fmin else None,
        "fecha_max": fmax.isoformat() if fmax else None,
        "total_horas": round(float(total_horas or 0), 2),
        "hs_viaje": round(float(hs_viaje or 0), 2),
        "hs50": round(float(hs50 or 0), 2),
        "hs_noc": round(float(hs_noc or 0), 2),
        "hs_noc50": round(float(hs_noc50 or 0), 2),
        "hs100": round(float(hs100 or 0), 2),
        "hs_extras": round(extras, 2),
        "total_hs_viaje": round(float(total_hs_viaje or 0), 2),
        "ausente": round(float(ausente or 0), 1),
        "enfermedad": round(float(enfermedad or 0), 1),
        "vacaciones": round(float(vacaciones or 0), 1),
        "licencia": round(float(licencia or 0), 1),
        "feriados": round(float(feriados or 0), 1),
        "accidente": round(float(accidente or 0), 1),
        "francos_comp": round(float(francos_comp or 0), 1),
        "d_normales": round(float(d_normales or 0), 1),
        "viandas": round(float(viandas or 0), 1),
        "traslado": round(float(traslado or 0), 1),
        "v_desayuno": round(float(desayunos or 0), 1),
        "fr_trabajados": round(float(fr_trab or 0), 1),
        "suspension": 0,
    }


def get_tot_hs_por_periodo(
    db: Session,
    periodo: Optional[str] = None,
    cliente: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    **_ignored,
) -> list[dict]:
    clauses = _tot_hs_filters(periodo, cliente, tipo_servicio)
    q = select(
        TotHs.periodo_desde,
        TotHs.periodo_hasta,
        func.coalesce(func.sum(TotHs.total_horas), 0),
        func.coalesce(func.sum(TotHs.hs50), 0),
        func.coalesce(func.sum(TotHs.hs100), 0),
        func.coalesce(func.sum(TotHs.hs_noc), 0),
        func.coalesce(func.sum(TotHs.hs_noc50), 0),
        func.count(TotHs.id),
        func.count(func.distinct(TotHs.empleado)),
    )
    for c in clauses:
        q = q.where(c)
    q = q.group_by(TotHs.periodo_desde, TotHs.periodo_hasta).order_by(
        TotHs.periodo_desde, TotHs.periodo_hasta
    )
    rows = db.execute(q).all()
    result = []
    for d, h, total, hs50, hs100, hs_noc, hs_noc50, regs, personas in rows:
        extras = float(hs50 or 0) + float(hs100 or 0) + float(hs_noc or 0) + float(hs_noc50 or 0)
        result.append(
            {
                "desde": d.isoformat(),
                "hasta": h.isoformat(),
                "periodo": f"{d.strftime('%d/%m/%y')}–{h.strftime('%d/%m/%y')}",
                "key": f"{d.isoformat()}|{h.isoformat()}",
                "total_horas": round(float(total or 0), 2),
                "hs_extras": round(extras, 2),
                "registros": int(regs or 0),
                "personas": int(personas or 0),
            }
        )
    return result


def get_tot_hs_por_mes(
    db: Session,
    periodo: Optional[str] = None,
    cliente: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    **_ignored,
) -> list[dict]:
    """Compat: el eje temporal real es el período cargado."""
    return get_tot_hs_por_periodo(db, periodo, cliente, tipo_servicio)


def get_tot_hs_por_sector(
    db: Session,
    periodo: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    **_ignored,
) -> list[dict]:
    """Agrupa por cliente (equivalente útil al «sector» del archivo real)."""
    clauses = _tot_hs_filters(periodo, None, tipo_servicio)
    q = select(
        TotHs.cliente,
        func.coalesce(func.sum(TotHs.total_horas), 0),
        func.coalesce(func.sum(TotHs.hs50), 0),
        func.coalesce(func.sum(TotHs.hs100), 0),
        func.coalesce(func.sum(TotHs.hs_noc), 0),
        func.coalesce(func.sum(TotHs.hs_noc50), 0),
        func.count(func.distinct(TotHs.empleado)),
        func.coalesce(func.sum(TotHs.ausente), 0),
        func.coalesce(func.sum(TotHs.vacaciones), 0),
    ).where(TotHs.cliente.isnot(None), TotHs.cliente != "")
    for c in clauses:
        q = q.where(c)
    q = q.group_by(TotHs.cliente)
    rows = db.execute(q).all()
    result = []
    for cliente, total, hs50, hs100, hs_noc, hs_noc50, personas, ausente, vacaciones in rows:
        extras = float(hs50 or 0) + float(hs100 or 0) + float(hs_noc or 0) + float(hs_noc50 or 0)
        result.append(
            {
                "sector": cliente,  # UI reutiliza «sector» como etiqueta del eje
                "cliente": cliente,
                "total_horas": round(float(total or 0), 2),
                "hs_extras": round(extras, 2),
                "personas": int(personas or 0),
                "ausente": round(float(ausente or 0), 1),
                "vacaciones": round(float(vacaciones or 0), 1),
                "horas_por_persona": round(float(total or 0) / personas, 1) if personas else 0,
            }
        )
    result.sort(key=lambda r: r["total_horas"], reverse=True)
    return result


def get_tot_hs_por_empleado(
    db: Session,
    periodo: Optional[str] = None,
    cliente: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    **_ignored,
) -> list[dict]:
    clauses = _tot_hs_filters(periodo, cliente, tipo_servicio)
    q = select(
        TotHs.empleado,
        func.coalesce(func.sum(TotHs.total_horas), 0),
        func.coalesce(func.sum(TotHs.hs_viaje), 0),
        func.coalesce(func.sum(TotHs.hs50), 0),
        func.coalesce(func.sum(TotHs.hs_noc), 0),
        func.coalesce(func.sum(TotHs.hs_noc50), 0),
        func.coalesce(func.sum(TotHs.hs100), 0),
        func.coalesce(func.sum(TotHs.total_hs_viaje), 0),
        func.coalesce(func.sum(TotHs.ausente), 0),
        func.coalesce(func.sum(TotHs.enfermedad), 0),
        func.coalesce(func.sum(TotHs.vacaciones), 0),
        func.coalesce(func.sum(TotHs.licencia), 0),
        func.coalesce(func.sum(TotHs.d_normales), 0),
        func.count(TotHs.id),
        func.min(TotHs.periodo_desde),
        func.max(TotHs.periodo_hasta),
    )
    for c in clauses:
        q = q.where(c)
    q = q.group_by(TotHs.empleado).order_by(func.sum(TotHs.total_horas).desc())
    rows = db.execute(q).all()
    result = []
    for row in rows:
        (
            empleado, total, hs_viaje, hs50, hs_noc, hs_noc50, hs100, total_hs_viaje,
            ausente, enfermedad, vacaciones, licencia, d_normales, filas, fmin, fmax,
        ) = row
        extras = float(hs50 or 0) + float(hs100 or 0) + float(hs_noc or 0) + float(hs_noc50 or 0)
        result.append(
            {
                "empleado": empleado,
                "sector": None,
                "total_horas": round(float(total or 0), 2),
                "hs_viaje": round(float(hs_viaje or 0), 2),
                "hs50": round(float(hs50 or 0), 2),
                "hs_noc": round(float(hs_noc or 0), 2),
                "hs_noc50": round(float(hs_noc50 or 0), 2),
                "hs100": round(float(hs100 or 0), 2),
                "hs_extras": round(extras, 2),
                "total_hs_viaje": round(float(total_hs_viaje or 0), 2),
                "ausente": round(float(ausente or 0), 1),
                "enfermedad": round(float(enfermedad or 0), 1),
                "vacaciones": round(float(vacaciones or 0), 1),
                "licencia": round(float(licencia or 0), 1),
                "d_normales": round(float(d_normales or 0), 1),
                "dias": int(filas or 0),
                "filas": int(filas or 0),
                "fecha_min": fmin.isoformat() if fmin else None,
                "fecha_max": fmax.isoformat() if fmax else None,
            }
        )
    return result


def get_tot_hs_detalle(
    db: Session,
    periodo: Optional[str] = None,
    cliente: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    empleado: Optional[str] = None,
    limit: int = 500,
    **_ignored,
) -> list[dict]:
    clauses = _tot_hs_filters(periodo, cliente, tipo_servicio, empleado)
    q = select(TotHs).order_by(
        TotHs.total_horas.desc(), TotHs.empleado, TotHs.servicio
    )
    for c in clauses:
        q = q.where(c)
    q = q.limit(max(1, min(limit, 2000)))
    rows = db.execute(q).scalars().all()
    return [
        {
            "periodo_desde": r.periodo_desde.isoformat() if r.periodo_desde else None,
            "periodo_hasta": r.periodo_hasta.isoformat() if r.periodo_hasta else None,
            "empleado": r.empleado,
            "servicio": r.servicio,
            "centro": r.centro,
            "cliente": r.cliente,
            "tipo_servicio": r.tipo_servicio,
            "total_horas": float(r.total_horas or 0),
            "hs_viaje": float(r.hs_viaje or 0),
            "hs50": float(r.hs50 or 0),
            "hs_noc": float(r.hs_noc or 0),
            "hs_noc50": float(r.hs_noc50 or 0),
            "hs100": float(r.hs100 or 0),
            "total_hs_viaje": float(r.total_hs_viaje or 0),
            "ausente": float(r.ausente or 0),
            "enfermedad": float(r.enfermedad or 0),
            "vacaciones": float(r.vacaciones or 0),
            "licencia": float(r.licencia or 0),
            "feriados": float(r.feriados or 0),
            "d_normales": float(r.d_normales or 0),
            "traslado": float(r.traslado or 0),
        }
        for r in rows
    ]
