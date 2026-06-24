from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_anios(db: Session) -> list[int]:
    rows = db.execute(
        text("SELECT DISTINCT strftime('%Y', fecha) as anio FROM registros ORDER BY anio")
    ).fetchall()
    return [int(r[0]) for r in rows if r[0]]


def get_sectores(db: Session) -> list[str]:
    rows = db.execute(
        text(
            "SELECT DISTINCT sector FROM registros "
            "WHERE sector IS NOT NULL AND sector != 'SIN DATO' ORDER BY sector"
        )
    ).fetchall()
    return [r[0] for r in rows]


def get_empleados(db: Session, sector: Optional[str] = None) -> list[str]:
    q = "SELECT DISTINCT empleado FROM registros WHERE empleado IS NOT NULL"
    params: dict = {}
    if sector:
        q += " AND sector = :sector"
        params["sector"] = sector
    q += " ORDER BY empleado"
    rows = db.execute(text(q), params).fetchall()
    return [r[0] for r in rows]


def get_deuda_vacaciones(
    db: Session,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    sector: Optional[str] = None,
) -> list[dict]:
    year_desde = int(desde[:4]) if desde else None
    year_hasta = int(hasta[:4]) if hasta else None

    q_planilla = """
        SELECT v.legajo, v.empleado, v.sector, v.anio,
               v.dias_disponibles, v.dias_tomados as tomados_planilla, v.dias_pendientes
        FROM vacaciones v
        WHERE 1=1
    """
    params: dict = {}
    if year_desde:
        q_planilla += " AND v.anio >= :year_desde"
        params["year_desde"] = year_desde
    if year_hasta:
        q_planilla += " AND v.anio <= :year_hasta"
        params["year_hasta"] = year_hasta
    if sector:
        q_planilla += " AND v.sector = :sector"
        params["sector"] = sector
    q_planilla += " ORDER BY v.empleado, v.anio"

    planilla_rows = db.execute(text(q_planilla), params).fetchall()

    q_real = """
        SELECT empleado, CAST(strftime('%Y', fecha) AS INTEGER) as anio_r, SUM(vacaciones) as dias_reales
        FROM registros
        WHERE 1=1
    """
    real_params: dict = {}
    if desde:
        q_real += " AND fecha >= :desde"
        real_params["desde"] = desde
    if hasta:
        q_real += " AND fecha <= :hasta"
        real_params["hasta"] = hasta
    q_real += " GROUP BY empleado, strftime('%Y', fecha)"

    real_rows = db.execute(text(q_real), real_params).fetchall()
    reales = {(r[0], r[1]): r[2] for r in real_rows}

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

    q = (
        "SELECT sector, SUM(dias_disponibles), SUM(dias_tomados), SUM(dias_pendientes) "
        "FROM vacaciones WHERE sector IS NOT NULL"
    )
    params: dict = {}
    if year_desde:
        q += " AND anio >= :year_desde"
        params["year_desde"] = year_desde
    if year_hasta:
        q += " AND anio <= :year_hasta"
        params["year_hasta"] = year_hasta
    q += " GROUP BY sector ORDER BY SUM(dias_pendientes) DESC"

    rows = db.execute(text(q), params).fetchall()
    return [
        {"sector": r[0], "disponibles": r[1] or 0, "tomados": r[2] or 0, "pendientes": r[3] or 0}
        for r in rows
    ]
