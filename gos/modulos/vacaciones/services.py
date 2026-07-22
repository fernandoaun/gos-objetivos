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
