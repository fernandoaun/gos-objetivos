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


def get_deuda_vacaciones(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sector: Optional[str] = None,
) -> list[dict]:
    year_desde = int(desde[:4]) if desde else None
    year_hasta = int(hasta[:4]) if hasta else None

    q_planilla = select(
        Vacacion.legajo,
        Vacacion.empleado,
        Vacacion.sector,
        Vacacion.anio,
        Vacacion.dias_disponibles,
        Vacacion.dias_tomados,
        Vacacion.dias_pendientes,
    )
    if year_desde:
        q_planilla = q_planilla.where(Vacacion.anio >= year_desde)
    if year_hasta:
        q_planilla = q_planilla.where(Vacacion.anio <= year_hasta)
    if sector:
        q_planilla = q_planilla.where(Vacacion.sector == sector)
    q_planilla = q_planilla.order_by(Vacacion.empleado, Vacacion.anio)
    planilla_rows = db.execute(q_planilla).all()

    q_real = select(
        Registro.empleado,
        extract("year", Registro.fecha).label("anio_r"),
        func.sum(Registro.vacaciones).label("dias_reales"),
    )
    if desde:
        q_real = q_real.where(Registro.fecha >= desde)
    if hasta:
        q_real = q_real.where(Registro.fecha <= hasta)
    q_real = q_real.group_by(Registro.empleado, extract("year", Registro.fecha))
    real_rows = db.execute(q_real).all()
    reales = {(r.empleado, int(r.anio_r)): r.dias_reales for r in real_rows if r.anio_r}

    result = []
    for row in planilla_rows:
        legajo, empleado, sect, anio_val, disponibles, tomados_planilla, pendientes = row
        tomados_real = reales.get((empleado, anio_val), 0)
        diferencia = (tomados_planilla or 0) - (tomados_real or 0)
        result.append(
            {
                "legajo": legajo,
                "empleado": empleado,
                "sector": sect,
                "anio": anio_val,
                "dias_disponibles": disponibles or 0,
                "tomados_planilla": tomados_planilla or 0,
                "tomados_real": int(tomados_real or 0),
                "dias_pendientes": pendientes or 0,
                "diferencia": diferencia,
            }
        )
    return result


def get_resumen_sector(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
) -> list[dict]:
    year_desde = int(desde[:4]) if desde else None
    year_hasta = int(hasta[:4]) if hasta else None

    q = select(
        Vacacion.sector,
        func.sum(Vacacion.dias_disponibles),
        func.sum(Vacacion.dias_tomados),
        func.sum(Vacacion.dias_pendientes),
    ).where(Vacacion.sector.isnot(None))
    if year_desde:
        q = q.where(Vacacion.anio >= year_desde)
    if year_hasta:
        q = q.where(Vacacion.anio <= year_hasta)
    q = q.group_by(Vacacion.sector).order_by(func.sum(Vacacion.dias_pendientes).desc())
    rows = db.execute(q).all()
    return [
        {"sector": r[0], "disponibles": r[1] or 0, "tomados": r[2] or 0, "pendientes": r[3] or 0}
        for r in rows
    ]
