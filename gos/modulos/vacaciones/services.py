from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import delete, extract, func, select, tuple_, union
from sqlalchemy.orm import Session

from gos.modulos.vacaciones.models import Registro, TotHs, Vacacion


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    raw = str(value).strip()[:10]
    if len(raw) < 10:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def get_anios(db: Session) -> list[int]:
    """Años con al menos un empleado con días pendientes (disponibles − tomados > 0).

    Si todos completaron un año, ese año deja de aparecer en filtros.
    """
    pendientes = func.coalesce(Vacacion.dias_disponibles, 0) - func.coalesce(
        Vacacion.dias_tomados, 0
    )
    rows = db.execute(
        select(Vacacion.anio)
        .where(Vacacion.anio.isnot(None), pendientes > 0)
        .distinct()
        .order_by(Vacacion.anio)
    ).scalars().all()
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


_MESES_ES = (
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


def _tot_hs_period_label(desde: date, hasta: date, *, with_year: bool = False) -> str:
    """Etiqueta del período: mes contable = mes de hasta (ej. 21/01–20/02 → Febrero)."""
    # Períodos mensuales típicos (~30 días, 21 al 20). Rangos largos conservan fechas.
    if (hasta - desde).days <= 40:
        name = _MESES_ES[hasta.month]
        return f"{name} {hasta.year}" if with_year else name
    return f"{desde.strftime('%d/%m/%Y')} al {hasta.strftime('%d/%m/%Y')}"


def _tot_hs_periods_overlap(a_desde: date, a_hasta: date, b_desde: date, b_hasta: date) -> bool:
    """True si los rangos coinciden o se pisan en al menos un día."""
    return a_desde <= b_hasta and a_hasta >= b_desde


def _tot_hs_periodos_con_recencia(db: Session) -> list[tuple[date, date, int]]:
    """Períodos distintos con max(id) como proxy de carga más reciente."""
    rows = db.execute(
        select(
            TotHs.periodo_desde,
            TotHs.periodo_hasta,
            func.max(TotHs.id),
        ).group_by(TotHs.periodo_desde, TotHs.periodo_hasta)
    ).all()
    return sorted(
        [(d, h, int(mid or 0)) for d, h, mid in rows],
        key=lambda r: r[2],
        reverse=True,
    )


def _active_tot_hs_period_pairs(db: Session) -> list[tuple[date, date]]:
    """Períodos visibles: si se solapan, gana el cargado más recientemente."""
    active: list[tuple[date, date]] = []
    for d, h, _mid in _tot_hs_periodos_con_recencia(db):
        if any(_tot_hs_periods_overlap(d, h, ad, ah) for ad, ah in active):
            continue
        active.append((d, h))
    return active


def purge_overlapping_tot_hs_periods(db: Session) -> list[dict]:
    """Borra períodos solapados más antiguos; deja solo el más reciente de cada choque."""
    ranked = _tot_hs_periodos_con_recencia(db)
    if len(ranked) < 2:
        return []
    keep: list[tuple[date, date]] = []
    drop: list[tuple[date, date]] = []
    for d, h, _mid in ranked:
        if any(_tot_hs_periods_overlap(d, h, kd, kh) for kd, kh in keep):
            drop.append((d, h))
        else:
            keep.append((d, h))
    if not drop:
        return []
    for d, h in drop:
        db.execute(
            delete(TotHs).where(
                TotHs.periodo_desde == d,
                TotHs.periodo_hasta == h,
            )
        )
    db.commit()
    return [
        {
            "desde": d.isoformat(),
            "hasta": h.isoformat(),
            "label": f"{d.strftime('%d/%m/%Y')} al {h.strftime('%d/%m/%Y')}",
        }
        for d, h in drop
    ]


def _tot_hs_filters(
    db: Session,
    periodo: Optional[str] = None,
    cliente: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    empleado: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
):
    clauses = []
    active = _active_tot_hs_period_pairs(db)
    if active:
        clauses.append(tuple_(TotHs.periodo_desde, TotHs.periodo_hasta).in_(active))
    else:
        clauses.append(TotHs.id == -1)
    d_desde = _parse_iso_date(desde)
    d_hasta = _parse_iso_date(hasta)
    key = _parse_period_key(periodo)
    if d_desde or d_hasta:
        # Solapamiento: períodos que tocan [desde, hasta].
        # Tot Hs. son totales del período completo (no se puede partir por día).
        if d_desde:
            clauses.append(TotHs.periodo_hasta >= d_desde)
        if d_hasta:
            clauses.append(TotHs.periodo_desde <= d_hasta)
    elif key:
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
    # Limpia solapes viejos ya cargados para que no aparezcan en la UI.
    purge_overlapping_tot_hs_periods(db)

    active = _active_tot_hs_period_pairs(db)
    with_year = len({h.year for _d, h in active}) > 1
    periodos = []
    for d, h in sorted(active, key=lambda p: (p[0], p[1])):
        periodos.append(
            {
                "desde": d.isoformat(),
                "hasta": h.isoformat(),
                "key": f"{d.isoformat()}|{h.isoformat()}",
                "label": _tot_hs_period_label(d, h, with_year=with_year),
            }
        )

    if active:
        q_tot = select(
            func.count(TotHs.id),
            func.count(func.distinct(TotHs.empleado)),
            func.min(TotHs.periodo_desde),
            func.max(TotHs.periodo_hasta),
        ).where(tuple_(TotHs.periodo_desde, TotHs.periodo_hasta).in_(active))
    else:
        q_tot = select(
            func.count(TotHs.id),
            func.count(func.distinct(TotHs.empleado)),
            func.min(TotHs.periodo_desde),
            func.max(TotHs.periodo_hasta),
        ).where(TotHs.id == -1)
    row = db.execute(q_tot).one()
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
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    **_ignored,
) -> dict:
    clauses = _tot_hs_filters(db, periodo, cliente, tipo_servicio, desde=desde, hasta=hasta)
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


_THS_COMPARE_METRICS = (
    # (key, label, of_hours) — of_hours: % sobre total_horas del período
    ("total_horas", "Total horas", True),
    ("hs_extras", "Hs. extras", True),
    ("hs50", "Hs 50%", True),
    ("hs100", "Hs 100%", True),
    ("hs_noc", "Hs nocturnas", True),
    ("hs_noc50", "Hs noct. 50%", True),
    ("hs_viaje", "Hs viaje", True),
    ("total_hs_viaje", "Total hs + viaje", True),
    ("personas", "Personas", False),
    ("d_normales", "Días normales", False),
    ("ausente", "Ausentes", False),
    ("vacaciones", "Vacaciones", False),
    ("enfermedad", "Enfermedad", False),
    ("licencia", "Licencias", False),
    ("feriados", "Feriados trab.", False),
    ("traslado", "Traslados", False),
    ("fr_trabajados", "Francos trabajados", False),
    ("francos_comp", "Francos compens.", False),
    ("viandas", "Viandas", False),
    ("v_desayuno", "Desayunos", False),
)


def _tot_hs_period_meta(db: Session, periodo: str) -> dict:
    key = _parse_period_key(periodo)
    if not key:
        return {"key": periodo, "label": periodo, "desde": None, "hasta": None}
    d = _parse_iso_date(key[0])
    h = _parse_iso_date(key[1])
    if not d or not h:
        return {"key": periodo, "label": periodo, "desde": key[0], "hasta": key[1]}
    return {
        "key": f"{d.isoformat()}|{h.isoformat()}",
        "label": _tot_hs_period_label(d, h),
        "desde": d.isoformat(),
        "hasta": h.isoformat(),
    }


def get_tot_hs_comparar(
    db: Session,
    periodo_a: str,
    periodo_b: str,
    cliente: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    **_ignored,
) -> dict:
    """Compara dos períodos: valores, % sobre total de horas y diferencias."""
    meta_a = _tot_hs_period_meta(db, periodo_a)
    meta_b = _tot_hs_period_meta(db, periodo_b)
    # Orden cronológico: A = más antiguo, B = más reciente
    if (meta_a.get("desde") or "") > (meta_b.get("desde") or ""):
        meta_a, meta_b = meta_b, meta_a
        periodo_a, periodo_b = periodo_b, periodo_a

    a = get_tot_hs_resumen(
        db, periodo=periodo_a, cliente=cliente, tipo_servicio=tipo_servicio
    )
    b = get_tot_hs_resumen(
        db, periodo=periodo_b, cliente=cliente, tipo_servicio=tipo_servicio
    )
    total_a = float(a.get("total_horas") or 0)
    total_b = float(b.get("total_horas") or 0)

    def _pct(value: float, total: float) -> Optional[float]:
        if total <= 0:
            return None
        return round(float(value) * 100.0 / total, 2)

    filas = []
    for key, label, of_hours in _THS_COMPARE_METRICS:
        va = float(a.get(key) or 0)
        vb = float(b.get(key) or 0)
        dif = round(vb - va, 2)
        pct_a = _pct(va, total_a) if of_hours else None
        pct_b = _pct(vb, total_b) if of_hours else None
        dif_pp = None
        if pct_a is not None and pct_b is not None:
            dif_pp = round(pct_b - pct_a, 2)
        var_pct = None
        if va != 0:
            var_pct = round((vb - va) * 100.0 / abs(va), 1)
        elif vb != 0:
            var_pct = 100.0
        filas.append(
            {
                "key": key,
                "label": label,
                "of_hours": of_hours,
                "a": round(va, 2),
                "b": round(vb, 2),
                "pct_a": pct_a,
                "pct_b": pct_b,
                "dif": dif,
                "dif_pp": dif_pp,
                "var_pct": var_pct,
            }
        )

    return {
        "a": {**meta_a, "total_horas": round(total_a, 2), "personas": a.get("personas", 0)},
        "b": {**meta_b, "total_horas": round(total_b, 2), "personas": b.get("personas", 0)},
        "filas": filas,
    }


def get_tot_hs_por_periodo(
    db: Session,
    periodo: Optional[str] = None,
    cliente: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    **_ignored,
) -> list[dict]:
    clauses = _tot_hs_filters(db, periodo, cliente, tipo_servicio, desde=desde, hasta=hasta)
    q = select(
        TotHs.periodo_desde,
        TotHs.periodo_hasta,
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
        func.count(TotHs.id),
        func.count(func.distinct(TotHs.empleado)),
    )
    for c in clauses:
        q = q.where(c)
    q = q.group_by(TotHs.periodo_desde, TotHs.periodo_hasta).order_by(
        TotHs.periodo_desde, TotHs.periodo_hasta
    )
    rows = db.execute(q).all()
    years = {h.year for d, h, *_rest in rows}
    with_year = len(years) > 1
    result = []
    for (
        d, h, total, hs_viaje, hs50, hs_noc, hs_noc50, hs100, total_hs_viaje,
        ausente, enfermedad, vacaciones, licencia, feriados,
        accidente, francos_comp, d_normales, viandas, traslado, desayunos, fr_trab,
        regs, personas,
    ) in rows:
        extras = float(hs50 or 0) + float(hs100 or 0) + float(hs_noc or 0) + float(hs_noc50 or 0)
        result.append(
            {
                "desde": d.isoformat(),
                "hasta": h.isoformat(),
                "periodo": _tot_hs_period_label(d, h, with_year=with_year),
                "key": f"{d.isoformat()}|{h.isoformat()}",
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
                "feriados": round(float(feriados or 0), 1),
                "accidente": round(float(accidente or 0), 1),
                "francos_comp": round(float(francos_comp or 0), 1),
                "d_normales": round(float(d_normales or 0), 1),
                "viandas": round(float(viandas or 0), 1),
                "traslado": round(float(traslado or 0), 1),
                "v_desayuno": round(float(desayunos or 0), 1),
                "fr_trabajados": round(float(fr_trab or 0), 1),
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
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    **_ignored,
) -> list[dict]:
    """Compat: el eje temporal real es el período cargado."""
    return get_tot_hs_por_periodo(
        db, periodo, cliente, tipo_servicio, desde=desde, hasta=hasta
    )


def get_tot_hs_por_sector(
    db: Session,
    periodo: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    **_ignored,
) -> list[dict]:
    """Agrupa por cliente (equivalente útil al «sector» del archivo real)."""
    clauses = _tot_hs_filters(db, periodo, None, tipo_servicio, desde=desde, hasta=hasta)
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
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    **_ignored,
) -> list[dict]:
    clauses = _tot_hs_filters(db, periodo, cliente, tipo_servicio, desde=desde, hasta=hasta)
    q = select(
        TotHs.empleado,
        func.coalesce(func.sum(TotHs.total_horas), 0),
        func.coalesce(func.sum(TotHs.hs_viaje), 0),
        func.coalesce(func.sum(TotHs.hs50), 0),
        func.coalesce(func.sum(TotHs.hs_noc), 0),
        func.coalesce(func.sum(TotHs.hs_noc50), 0),
        func.coalesce(func.sum(TotHs.hs100), 0),
        func.coalesce(func.sum(TotHs.viandas), 0),
        func.coalesce(func.sum(TotHs.v_desayuno), 0),
        func.coalesce(func.sum(TotHs.d_normales), 0),
        func.coalesce(func.sum(TotHs.ausente), 0),
        func.coalesce(func.sum(TotHs.fr_trabajados), 0),
        func.coalesce(func.sum(TotHs.feriados), 0),
        func.coalesce(func.sum(TotHs.enfermedad), 0),
        func.coalesce(func.sum(TotHs.traslado), 0),
        func.coalesce(func.sum(TotHs.vacaciones), 0),
        func.coalesce(func.sum(TotHs.licencia), 0),
        func.coalesce(func.sum(TotHs.accidente), 0),
        func.coalesce(func.sum(TotHs.francos_comp), 0),
        func.coalesce(func.sum(TotHs.total_hs_viaje), 0),
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
            empleado, total, hs_viaje, hs50, hs_noc, hs_noc50, hs100,
            viandas, desayunos, d_normales, ausente, fr_trab, feriados,
            enfermedad, traslado, vacaciones, licencia, accidente, francos_comp,
            total_hs_viaje, filas, fmin, fmax,
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
                "viandas": round(float(viandas or 0), 1),
                "v_desayuno": round(float(desayunos or 0), 1),
                "d_normales": round(float(d_normales or 0), 1),
                "ausente": round(float(ausente or 0), 1),
                "fr_trabajados": round(float(fr_trab or 0), 1),
                "feriados": round(float(feriados or 0), 1),
                "enfermedad": round(float(enfermedad or 0), 1),
                "traslado": round(float(traslado or 0), 1),
                "vacaciones": round(float(vacaciones or 0), 1),
                "licencia": round(float(licencia or 0), 1),
                "accidente": round(float(accidente or 0), 1),
                "francos_comp": round(float(francos_comp or 0), 1),
                "total_hs_viaje": round(float(total_hs_viaje or 0), 2),
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
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    limit: int = 500,
    **_ignored,
) -> list[dict]:
    clauses = _tot_hs_filters(
        db, periodo, cliente, tipo_servicio, empleado, desde=desde, hasta=hasta
    )
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
            "viandas": float(r.viandas or 0),
            "v_desayuno": float(r.v_desayuno or 0),
            "d_normales": float(r.d_normales or 0),
            "ausente": float(r.ausente or 0),
            "fr_trabajados": float(r.fr_trabajados or 0),
            "feriados": float(r.feriados or 0),
            "enfermedad": float(r.enfermedad or 0),
            "traslado": float(r.traslado or 0),
            "vacaciones": float(r.vacaciones or 0),
            "licencia": float(r.licencia or 0),
            "accidente": float(r.accidente or 0),
            "francos_comp": float(r.francos_comp or 0),
        }
        for r in rows
    ]
