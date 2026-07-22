"""Consultas del plan de mantenimiento y VTV."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from gos.modulos.mantenimiento.models import MantPlanCelda, MantPlanMeta, MantUnidad, MantVtv

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

VTV_ALERTA_DIAS = 60


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


def get_vtv(session: Session, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    alerta = hoy + timedelta(days=VTV_ALERTA_DIAS)

    rows = session.execute(
        select(MantVtv)
        .options(joinedload(MantVtv.unidad))
        .join(MantUnidad)
        .order_by(MantVtv.vencimiento, MantUnidad.nombre)
    ).scalars().all()

    items = []
    vencidas = 0
    por_vencer = 0
    vigentes = 0
    for v in rows:
        dias = (v.vencimiento - hoy).days
        if dias < 0:
            estado = "vencida"
            vencidas += 1
        elif v.vencimiento <= alerta:
            estado = "por_vencer"
            por_vencer += 1
        else:
            estado = "vigente"
            vigentes += 1
        items.append(
            {
                "unidad_id": v.unidad_id,
                "codigo": v.unidad.codigo,
                "nombre": v.unidad.nombre,
                "vencimiento": v.vencimiento.isoformat(),
                "dias": dias,
                "estado": estado,
            }
        )

    return {
        "hoy": hoy.isoformat(),
        "alerta_dias": VTV_ALERTA_DIAS,
        "kpis": {
            "total": len(items),
            "vencidas": vencidas,
            "por_vencer": por_vencer,
            "vigentes": vigentes,
        },
        "items": items,
    }
