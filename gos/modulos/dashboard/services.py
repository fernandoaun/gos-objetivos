"""Agrega métricas livianas de todos los módulos GOS para el Command Center."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select

from gos.extensions import db


def build_summary(empresa_id: int) -> dict[str, Any]:
    modules = [
        _safe("objetivos", _objetivos, empresa_id),
        _safe("capacitacion", _capacitacion, empresa_id),
        _safe("hwo", _hwo, empresa_id),
        _safe("vacaciones", _vacaciones, empresa_id),
        _safe("ralenti", _ralenti, empresa_id),
        _safe("mantenimiento", _mantenimiento, empresa_id),
    ]

    scores = [m["score"] for m in modules if m.get("ok") and m.get("score") is not None]
    health = round(sum(scores) / len(scores), 1) if scores else None
    alerts = sum(int(m.get("alerts") or 0) for m in modules if m.get("ok"))

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "empresa_id": empresa_id,
        "health": health,
        "alerts": alerts,
        "modules_ok": sum(1 for m in modules if m.get("ok")),
        "modules_total": len(modules),
        "modules": modules,
        "series": {
            "scores": [
                {"code": m["code"], "label": m["label"], "value": m.get("score") or 0}
                for m in modules
            ],
            "alerts": [
                {"code": m["code"], "label": m["label"], "value": int(m.get("alerts") or 0)}
                for m in modules
            ],
        },
    }


def _safe(code: str, fn, empresa_id: int) -> dict[str, Any]:
    meta = MODULE_META[code]
    try:
        payload = fn(empresa_id)
        payload.update(meta)
        payload["ok"] = True
        payload.setdefault("error", None)
        return payload
    except Exception as exc:
        return {
            **meta,
            "ok": False,
            "error": str(exc),
            "score": None,
            "alerts": 0,
            "headline": "—",
            "metrics": [],
            "bars": [],
        }


MODULE_META = {
    "objetivos": {
        "code": "objetivos",
        "label": "Objetivos",
        "url": "/gos/objetivos/dashboard/",
        "color": "#00e5ff",
    },
    "capacitacion": {
        "code": "capacitacion",
        "label": "Capacitación",
        "url": "/gos/capacitacion/",
        "color": "#ff2d95",
    },
    "hwo": {
        "code": "hwo",
        "label": "Análisis",
        "url": "/gos/hwo/",
        "color": "#b8ff3c",
    },
    "vacaciones": {
        "code": "vacaciones",
        "label": "Vacaciones",
        "url": "/gos/vacaciones/",
        "color": "#ff9f1c",
    },
    "ralenti": {
        "code": "ralenti",
        "label": "Ralentí",
        "url": "/gos/ralenti/",
        "color": "#7b61ff",
    },
    "mantenimiento": {
        "code": "mantenimiento",
        "label": "Mantenimiento",
        "url": "/gos/mantenimiento/",
        "color": "#2afadf",
    },
}


def _objetivos(empresa_id: int) -> dict[str, Any]:
    from gos.modulos.objetivos.services.reportes_service import generar_informe_cumplimiento

    informe = generar_informe_cumplimiento(empresa_id)
    score = informe.pct_kpis_cumplidos
    if score is None:
        score = informe.pct_objetivos_cumplidos
    bars = []
    for obj in informe.objetivos[:8]:
        bars.append(
            {
                "label": obj.codigo,
                "value": float(obj.pct_cumplimiento or 0),
            }
        )
    return {
        "score": round(float(score), 1) if score is not None else None,
        "alerts": int(informe.kpis_fuera or 0),
        "headline": (
            f"{informe.pct_kpis_cumplidos:.0f}% KPI"
            if informe.pct_kpis_cumplidos is not None
            else "Sin datos"
        ),
        "metrics": [
            {"label": "Objetivos", "value": informe.total_objetivos},
            {"label": "KPI", "value": informe.total_kpis},
            {"label": "En meta", "value": informe.kpis_cumplidos},
            {"label": "Fuera", "value": informe.kpis_fuera},
        ],
        "bars": bars,
    }


def _capacitacion(empresa_id: int) -> dict[str, Any]:
    """Resumen liviano (sin analitico por persona)."""
    from gos.modulos.capacitacion.models import (
        AlertaCapacitacion,
        Curso,
        Participante,
        RegistroCapacitacion,
    )

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    personas = Participante.query.filter_by(empresa_id=empresa_id, activo=True).count()
    cursos = Curso.query.filter_by(empresa_id=empresa_id, activo=True).count()
    realizadas_mes = (
        RegistroCapacitacion.query.filter_by(empresa_id=empresa_id)
        .filter(RegistroCapacitacion.fecha_realizacion >= inicio_mes)
        .count()
    )
    alertas = AlertaCapacitacion.query.filter_by(
        empresa_id=empresa_id, resuelta=False
    ).count()

    # Score proxy: presencia de actividad vs alertas abiertas
    if personas == 0:
        score = None
    else:
        pressure = min(100, alertas * 8)
        activity = min(40, realizadas_mes * 4)
        score = max(0, min(100, 70 + activity - pressure))

    # Evolución simple últimos 6 meses
    bars = []
    for i in range(5, -1, -1):
        y = hoy.year
        m = hoy.month - i
        while m <= 0:
            m += 12
            y -= 1
        start = date(y, m, 1)
        if m == 12:
            end = date(y + 1, 1, 1)
        else:
            end = date(y, m + 1, 1)
        n = (
            RegistroCapacitacion.query.filter_by(empresa_id=empresa_id)
            .filter(RegistroCapacitacion.fecha_realizacion >= start)
            .filter(RegistroCapacitacion.fecha_realizacion < end)
            .count()
        )
        bars.append({"label": f"{m:02d}", "value": float(n)})

    return {
        "score": round(float(score), 1) if score is not None else None,
        "alerts": int(alertas),
        "headline": f"{personas} personas",
        "metrics": [
            {"label": "Personas", "value": personas},
            {"label": "Cursos", "value": cursos},
            {"label": "Mes", "value": realizadas_mes},
            {"label": "Alertas", "value": alertas},
        ],
        "bars": bars,
    }


def _hwo(_empresa_id: int) -> dict[str, Any]:
    from gos.modulos.hwo import storage

    datasets = storage.get_all_datasets()
    n = len(datasets)
    score = 100.0 if n else None
    bars = [
        {
            "label": (d.get("name") or "?")[:10],
            "value": float(d.get("row_count") or 0),
        }
        for d in datasets[:8]
    ]
    if not bars:
        bars = [{"label": "—", "value": 0}]

    return {
        "score": score,
        "alerts": 0 if n else 1,
        "headline": f"{n} datasets" if n else "Sin datasets",
        "metrics": [
            {"label": "Datasets", "value": n},
            {
                "label": "Filas",
                "value": sum(int(d.get("row_count") or 0) for d in datasets),
            },
        ],
        "bars": bars,
    }


def _vacaciones(_empresa_id: int) -> dict[str, Any]:
    from gos.modulos.vacaciones import services as vac_services
    from gos.modulos.vacaciones.models import Vacacion

    resumen = vac_services.get_resumen_sector(db.session)
    tot = vac_services.get_tot_hs_resumen(db.session)

    disp = sum(float(r.get("disponibles") or 0) for r in resumen)
    tom = sum(float(r.get("tomados") or 0) for r in resumen)
    pend = sum(float(r.get("pendientes") or 0) for r in resumen)
    personas = (
        db.session.execute(select(func.count(func.distinct(Vacacion.empleado)))).scalar() or 0
    )

    score = round((tom / disp) * 100, 1) if disp > 0 else None
    bars = [
        {"label": (r.get("sector") or "?")[:8], "value": float(r.get("pendientes") or 0)}
        for r in resumen[:8]
    ]

    return {
        "score": score,
        "alerts": int(max(0, round(pend / 10))) if pend else 0,
        "headline": f"{pend:.0f} días pend." if resumen else "Sin datos",
        "metrics": [
            {"label": "Personas", "value": int(personas)},
            {"label": "Pendientes", "value": round(pend, 1)},
            {"label": "Hs totales", "value": tot.get("total_horas") or 0},
            {"label": "Sectores", "value": len(resumen)},
        ],
        "bars": bars or [{"label": "—", "value": 0}],
    }


def _ralenti(_empresa_id: int) -> dict[str, Any]:
    from gos.modulos.ralenti.models import RalentiEvent

    row = db.session.execute(
        select(
            func.count(RalentiEvent.id),
            func.coalesce(func.sum(RalentiEvent.dur_min), 0),
            func.coalesce(func.sum(RalentiEvent.litros), 0),
            func.count(func.distinct(RalentiEvent.vehiculo)),
        )
    ).one()
    eventos, mins, litros, vehiculos = row
    horas = round(float(mins or 0) / 60.0, 1)

    # Menos horas de ralentí = mejor score (proxy)
    if int(eventos or 0) == 0:
        score = None
    else:
        score = max(0.0, min(100.0, 100.0 - min(80.0, horas / 2)))

    # Top vehículos por minutos
    top = db.session.execute(
        select(
            RalentiEvent.vehiculo,
            func.coalesce(func.sum(RalentiEvent.dur_min), 0).label("mins"),
        )
        .where(RalentiEvent.vehiculo.isnot(None), RalentiEvent.vehiculo != "")
        .group_by(RalentiEvent.vehiculo)
        .order_by(func.sum(RalentiEvent.dur_min).desc())
        .limit(8)
    ).all()
    bars = [
        {"label": (v or "?")[:8], "value": round(float(m or 0) / 60.0, 2)}
        for v, m in top
    ]

    return {
        "score": round(score, 1) if score is not None else None,
        "alerts": 1 if horas > 100 else 0,
        "headline": f"{horas} h ralentí",
        "metrics": [
            {"label": "Eventos", "value": int(eventos or 0)},
            {"label": "Horas", "value": horas},
            {"label": "Litros", "value": round(float(litros or 0), 1)},
            {"label": "Unidades", "value": int(vehiculos or 0)},
        ],
        "bars": bars or [{"label": "—", "value": 0}],
    }


def _mantenimiento(_empresa_id: int) -> dict[str, Any]:
    from gos.modulos.mantenimiento import services as mant_services

    plan = mant_services.get_plan(db.session)
    vtv = mant_services.get_vtv(db.session)
    kpis = plan.get("kpis") or {}
    vk = vtv.get("kpis") or {}

    cumplimiento = kpis.get("cumplimiento")
    score = round(float(cumplimiento) * 100, 1) if cumplimiento is not None else None
    alerts = int(vk.get("vencidas") or 0) + int(vk.get("por_vencer") or 0)

    bars = []
    for m in (plan.get("por_mes") or [])[:12]:
        c = m.get("cumplimiento")
        bars.append(
            {
                "label": (m.get("label") or str(m.get("mes")))[:3],
                "value": round(float(c) * 100, 1) if c is not None else 0,
            }
        )

    return {
        "score": score,
        "alerts": alerts,
        "headline": (
            f"{score:.0f}% plan"
            if score is not None
            else f"{vk.get('total', 0)} VTV"
        ),
        "metrics": [
            {"label": "Unidades", "value": kpis.get("unidades") or 0},
            {"label": "Cumplim.", "value": f"{score}%" if score is not None else "—"},
            {"label": "VTV venc.", "value": vk.get("vencidas") or 0},
            {"label": "Por vencer", "value": vk.get("por_vencer") or 0},
        ],
        "bars": bars or [{"label": "—", "value": 0}],
    }
