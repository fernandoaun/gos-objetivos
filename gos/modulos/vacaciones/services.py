from __future__ import annotations

from typing import Optional

from sqlalchemy import extract, func, select, union
from sqlalchemy.orm import Session

from gos.modulos.vacaciones.models import Registro, Vacacion


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


def _registro_filters(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sector: Optional[str] = None,
    anios: Optional[list[int]] = None,
    empleado: Optional[str] = None,
):
    """Filtros comunes sobre Registro para el dashboard Tot Hs."""
    years = _resolve_anios(anios, desde, hasta)
    clauses = []
    if years:
        clauses.append(extract("year", Registro.fecha).in_(years))
    else:
        if desde:
            clauses.append(Registro.fecha >= desde)
        if hasta:
            clauses.append(Registro.fecha <= hasta)
    if sector:
        clauses.append(Registro.sector == sector)
    if empleado:
        clauses.append(Registro.empleado == empleado)
    return clauses


def get_tot_hs_meta(db: Session) -> dict:
    """Rango de fechas y años disponibles en registros diarios."""
    row = db.execute(
        select(
            func.min(Registro.fecha),
            func.max(Registro.fecha),
            func.count(Registro.id),
            func.count(func.distinct(Registro.empleado)),
        )
    ).one()
    fecha_min, fecha_max, total, personas = row
    anios = db.execute(
        select(extract("year", Registro.fecha).label("anio"))
        .where(Registro.fecha.isnot(None))
        .distinct()
        .order_by(extract("year", Registro.fecha))
    ).scalars().all()
    return {
        "fecha_min": fecha_min.isoformat() if fecha_min else None,
        "fecha_max": fecha_max.isoformat() if fecha_max else None,
        "total_registros": int(total or 0),
        "personas": int(personas or 0),
        "anios": [int(a) for a in anios if a is not None],
    }


def get_tot_hs_resumen(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sector: Optional[str] = None,
    anios: Optional[list[int]] = None,
) -> dict:
    """KPIs agregados de horas y novedades."""
    clauses = _registro_filters(desde, hasta, sector, anios)
    q = select(
        func.count(Registro.id),
        func.count(func.distinct(Registro.empleado)),
        func.min(Registro.fecha),
        func.max(Registro.fecha),
        func.coalesce(func.sum(Registro.total_horas), 0),
        func.coalesce(func.sum(Registro.hs_viaje), 0),
        func.coalesce(func.sum(Registro.hs50), 0),
        func.coalesce(func.sum(Registro.hs_noc), 0),
        func.coalesce(func.sum(Registro.hs_noc50), 0),
        func.coalesce(func.sum(Registro.hs100), 0),
        func.coalesce(func.sum(Registro.ausente), 0),
        func.coalesce(func.sum(Registro.enfermedad), 0),
        func.coalesce(func.sum(Registro.vacaciones), 0),
        func.coalesce(func.sum(Registro.licencia), 0),
        func.coalesce(func.sum(Registro.feriados), 0),
        func.coalesce(func.sum(Registro.accidente), 0),
        func.coalesce(func.sum(Registro.suspension), 0),
        func.coalesce(func.sum(Registro.francos_comp), 0),
        func.coalesce(func.sum(Registro.d_normales), 0),
        func.coalesce(func.sum(Registro.viandas), 0),
    )
    for c in clauses:
        q = q.where(c)
    row = db.execute(q).one()
    (
        registros, personas, fmin, fmax,
        total_horas, hs_viaje, hs50, hs_noc, hs_noc50, hs100,
        ausente, enfermedad, vacaciones, licencia, feriados,
        accidente, suspension, francos_comp, d_normales, viandas,
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
        "ausente": int(ausente or 0),
        "enfermedad": int(enfermedad or 0),
        "vacaciones": int(vacaciones or 0),
        "licencia": int(licencia or 0),
        "feriados": int(feriados or 0),
        "accidente": int(accidente or 0),
        "suspension": int(suspension or 0),
        "francos_comp": int(francos_comp or 0),
        "d_normales": int(d_normales or 0),
        "viandas": int(viandas or 0),
    }


def get_tot_hs_por_mes(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sector: Optional[str] = None,
    anios: Optional[list[int]] = None,
) -> list[dict]:
    clauses = _registro_filters(desde, hasta, sector, anios)
    year_col = extract("year", Registro.fecha).label("anio")
    month_col = extract("month", Registro.fecha).label("mes")
    q = select(
        year_col,
        month_col,
        func.coalesce(func.sum(Registro.total_horas), 0),
        func.coalesce(func.sum(Registro.hs50), 0),
        func.coalesce(func.sum(Registro.hs100), 0),
        func.coalesce(func.sum(Registro.hs_noc), 0),
        func.coalesce(func.sum(Registro.hs_noc50), 0),
        func.count(Registro.id),
        func.count(func.distinct(Registro.empleado)),
    )
    for c in clauses:
        q = q.where(c)
    q = q.group_by(year_col, month_col).order_by(year_col, month_col)
    rows = db.execute(q).all()
    result = []
    for anio, mes, total, hs50, hs100, hs_noc, hs_noc50, regs, personas in rows:
        extras = float(hs50 or 0) + float(hs100 or 0) + float(hs_noc or 0) + float(hs_noc50 or 0)
        result.append(
            {
                "anio": int(anio),
                "mes": int(mes),
                "periodo": f"{int(anio)}-{int(mes):02d}",
                "total_horas": round(float(total or 0), 2),
                "hs_extras": round(extras, 2),
                "registros": int(regs or 0),
                "personas": int(personas or 0),
            }
        )
    return result


def get_tot_hs_por_sector(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    anios: Optional[list[int]] = None,
) -> list[dict]:
    clauses = _registro_filters(desde, hasta, None, anios)
    q = select(
        Registro.sector,
        func.coalesce(func.sum(Registro.total_horas), 0),
        func.coalesce(func.sum(Registro.hs50), 0),
        func.coalesce(func.sum(Registro.hs100), 0),
        func.coalesce(func.sum(Registro.hs_noc), 0),
        func.coalesce(func.sum(Registro.hs_noc50), 0),
        func.count(func.distinct(Registro.empleado)),
        func.coalesce(func.sum(Registro.ausente), 0),
        func.coalesce(func.sum(Registro.vacaciones), 0),
    ).where(Registro.sector.isnot(None), Registro.sector != "")
    for c in clauses:
        q = q.where(c)
    q = q.group_by(Registro.sector)
    rows = db.execute(q).all()
    result = []
    for sector, total, hs50, hs100, hs_noc, hs_noc50, personas, ausente, vacaciones in rows:
        extras = float(hs50 or 0) + float(hs100 or 0) + float(hs_noc or 0) + float(hs_noc50 or 0)
        result.append(
            {
                "sector": sector,
                "total_horas": round(float(total or 0), 2),
                "hs_extras": round(extras, 2),
                "personas": int(personas or 0),
                "ausente": int(ausente or 0),
                "vacaciones": int(vacaciones or 0),
                "horas_por_persona": round(float(total or 0) / personas, 1) if personas else 0,
            }
        )
    result.sort(key=lambda r: r["total_horas"], reverse=True)
    return result


def get_tot_hs_por_empleado(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sector: Optional[str] = None,
    anios: Optional[list[int]] = None,
) -> list[dict]:
    clauses = _registro_filters(desde, hasta, sector, anios)
    q = select(
        Registro.empleado,
        Registro.sector,
        func.coalesce(func.sum(Registro.total_horas), 0),
        func.coalesce(func.sum(Registro.hs_viaje), 0),
        func.coalesce(func.sum(Registro.hs50), 0),
        func.coalesce(func.sum(Registro.hs_noc), 0),
        func.coalesce(func.sum(Registro.hs_noc50), 0),
        func.coalesce(func.sum(Registro.hs100), 0),
        func.coalesce(func.sum(Registro.ausente), 0),
        func.coalesce(func.sum(Registro.enfermedad), 0),
        func.coalesce(func.sum(Registro.vacaciones), 0),
        func.coalesce(func.sum(Registro.licencia), 0),
        func.coalesce(func.sum(Registro.d_normales), 0),
        func.count(Registro.id),
        func.min(Registro.fecha),
        func.max(Registro.fecha),
    )
    for c in clauses:
        q = q.where(c)
    q = q.group_by(Registro.empleado, Registro.sector).order_by(
        func.sum(Registro.total_horas).desc()
    )
    rows = db.execute(q).all()
    result = []
    for row in rows:
        (
            empleado, sect, total, hs_viaje, hs50, hs_noc, hs_noc50, hs100,
            ausente, enfermedad, vacaciones, licencia, d_normales, dias, fmin, fmax,
        ) = row
        extras = float(hs50 or 0) + float(hs100 or 0) + float(hs_noc or 0) + float(hs_noc50 or 0)
        result.append(
            {
                "empleado": empleado,
                "sector": sect,
                "total_horas": round(float(total or 0), 2),
                "hs_viaje": round(float(hs_viaje or 0), 2),
                "hs50": round(float(hs50 or 0), 2),
                "hs_noc": round(float(hs_noc or 0), 2),
                "hs_noc50": round(float(hs_noc50 or 0), 2),
                "hs100": round(float(hs100 or 0), 2),
                "hs_extras": round(extras, 2),
                "ausente": int(ausente or 0),
                "enfermedad": int(enfermedad or 0),
                "vacaciones": int(vacaciones or 0),
                "licencia": int(licencia or 0),
                "d_normales": int(d_normales or 0),
                "dias": int(dias or 0),
                "fecha_min": fmin.isoformat() if fmin else None,
                "fecha_max": fmax.isoformat() if fmax else None,
            }
        )
    return result


def get_tot_hs_detalle(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sector: Optional[str] = None,
    anios: Optional[list[int]] = None,
    empleado: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """Últimos registros diarios (para drill-down)."""
    clauses = _registro_filters(desde, hasta, sector, anios, empleado)
    q = select(Registro).order_by(Registro.fecha.desc(), Registro.empleado)
    for c in clauses:
        q = q.where(c)
    q = q.limit(max(1, min(limit, 2000)))
    rows = db.execute(q).scalars().all()
    return [
        {
            "fecha": r.fecha.isoformat() if r.fecha else None,
            "empleado": r.empleado,
            "sector": r.sector,
            "servicio": r.servicio,
            "centro": r.centro,
            "situacion": r.situacion,
            "total_horas": float(r.total_horas or 0),
            "hs_viaje": float(r.hs_viaje or 0),
            "hs50": float(r.hs50 or 0),
            "hs_noc": float(r.hs_noc or 0),
            "hs_noc50": float(r.hs_noc50 or 0),
            "hs100": float(r.hs100 or 0),
            "ausente": int(r.ausente or 0),
            "enfermedad": int(r.enfermedad or 0),
            "vacaciones": int(r.vacaciones or 0),
            "licencia": int(r.licencia or 0),
            "feriados": int(r.feriados or 0),
            "d_normales": int(r.d_normales or 0),
        }
        for r in rows
    ]
