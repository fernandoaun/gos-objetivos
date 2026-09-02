"""Recolecta datos reales de cada módulo para armar la presentación."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from flask_login import current_user

from gos.services.modulo_service import codigos_modulos_permitidos
from gos.services.presentacion_catalog import (
    get_module,
    list_modules_for_user,
    resolve_submodulos,
)
from gos.services.presentacion_pptx import build_presentation


def catalogo_presentaciones() -> list[dict]:
    permitidos = codigos_modulos_permitidos(current_user)
    return list_modules_for_user(permitidos)


def generar_pptx(module_code: str, submodulo_codes: list[str] | None = None) -> tuple[bytes, str]:
    permitidos = codigos_modulos_permitidos(current_user)
    if permitidos is not None and module_code not in permitidos:
        raise PermissionError("Sin acceso a ese módulo.")

    module = get_module(module_code)
    if not module:
        raise ValueError("Módulo no encontrado.")

    selected = resolve_submodulos(module_code, submodulo_codes)
    selected_codes = {s["code"] for s in selected}
    pack = _pack_datos(module_code)
    empresa = _empresa_nombre()

    slides = []
    for slide in pack.get("slides") or []:
        tags = set(slide.get("tags") or [])
        if not tags or tags & selected_codes:
            slides.append(slide)

    # Si no hay slides etiquetados, caer a 1 slide por submódulo
    if not slides:
        for sub in selected:
            extra = (pack.get("por_submodulo") or {}).get(sub["code"]) or {}
            block = {**sub, **extra}
            slides.append(block)

    payload = build_presentation(
        module,
        slides,
        overview_kpis=pack.get("overview_kpis") or [],
        chips=pack.get("chips") or [s["label"] for s in module.get("submodulos", [])][:6],
        periodo=pack.get("periodo") or "",
        empresa=empresa,
        dark_bar=pack.get("dark_bar"),
        circuit=pack.get("circuit"),
    )
    stamp = date.today().strftime("%Y%m%d")
    filename = f"Presentacion_{module['label'].replace(' ', '_')}_GOS_{stamp}.pptx"
    return payload, filename


def _empresa_id() -> int | None:
    try:
        if current_user.is_authenticated and current_user.empresa_id:
            return int(current_user.empresa_id)
    except Exception:
        return None
    return None


def _empresa_nombre() -> str:
    try:
        if current_user.is_authenticated and getattr(current_user, "empresa", None):
            nombre = (current_user.empresa.nombre or "").strip()
            if nombre:
                return nombre.upper()
    except Exception:
        pass
    return "GREEN OIL SERVICES"


def _fmt(n: Any) -> str:
    if n is None:
        return "—"
    if isinstance(n, float):
        if abs(n - int(n)) < 1e-9:
            n = int(n)
        else:
            return f"{n:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if isinstance(n, int):
        return f"{n:,}".replace(",", ".")
    return str(n)


def _pct(v: Any, *, ratio: bool = False) -> str:
    if v is None:
        return "—"
    try:
        x = float(v)
    except (TypeError, ValueError):
        return str(v)
    if ratio and abs(x) <= 1.5:
        x *= 100
    return f"{int(round(x))}%"


def _bar_pct(valor, items: list, key="valor") -> float:
    try:
        vals = [float(i.get(key) or 0) for i in items]
        mx = max(vals) if vals else 0
        v = float(valor or 0)
        return (v / mx) if mx else 0
    except Exception:
        return 0


def _rank(items: list[dict], *, label="label", value="valor", limit=10) -> list[dict]:
    out = []
    for i, it in enumerate(items[:limit], 1):
        out.append(
            {
                "rank": f"{i:02d}",
                "label": str(it.get(label) or "—"),
                "value": _fmt(it.get(value)),
            }
        )
    return out


def _pack_datos(module_code: str) -> dict:
    try:
        if module_code == "mantenimiento":
            return _pack_mantenimiento()
        if module_code == "capacitacion":
            from flask import current_app

            if not current_app.config.get("GOS_CAPACITACION_ENABLED"):
                return {}
            return _pack_capacitacion()
        if module_code == "vacaciones":
            return _pack_vacaciones()
        if module_code == "ralenti":
            return _pack_ralenti()
        if module_code == "objetivos":
            return _pack_objetivos()
        if module_code == "om":
            return _pack_om()
        if module_code == "recursos":
            return _pack_recursos()
        if module_code == "hwo":
            return _pack_hwo()
        if module_code == "dashboard":
            return _pack_dashboard()
    except Exception:
        return {}
    return {}


# ── Mantenimiento (estilo presentación de referencia) ───────────────────────


def _pack_mantenimiento() -> dict:
    from gos.extensions import db
    from gos.modulos.mantenimiento import services as mant

    session = db.session
    hist = mant.get_reporte_mensual(session, todos=True) or {}
    anio_actual = (hist.get("anios") or [date.today().year])[0]
    actual = mant.get_reporte_mensual(session, anio=anio_actual) or {}
    plan = mant.get_plan(session) or {}
    vtv = mant.get_vtv(session) or {}

    hk = hist.get("kpis") or {}
    ak = actual.get("kpis") or {}
    pk = plan.get("kpis") or {}
    vk = vtv.get("kpis") or {}
    anios = hist.get("anios") or []
    periodo = f"{min(anios)} – {max(anios)}" if anios else str(anio_actual)

    overview = [
        {"value": _fmt(hk.get("tareas")), "label": f"tareas ejecutadas\n{periodo}"},
        {"value": _fmt(hk.get("ordenes")), "label": "órdenes de mantenimiento"},
        {"value": _fmt(hk.get("unidades_con_orden")), "label": "unidades de flota atendidas"},
        {"value": _fmt(hk.get("horas")), "label": "horas hombre invertidas"},
    ]

    # Circuito / especialidades desde horas_por_clase
    clases = hist.get("horas_por_clase") or hist.get("tareas_por_clase") or []
    circuit_cards = []
    for item, letter, accent in zip(
        clases[:4],
        ["M", "S", "E", "L"],
        ["dark", "green", "dark", "gold"],
    ):
        circuit_cards.append(
            {
                "letter": letter,
                "title": item.get("label") or "—",
                "text": f"{_fmt(item.get('valor'))} hs · categoría operativa",
                "accent": accent,
            }
        )

    personal = hist.get("personal_activos") or actual.get("personal_activos") or []
    por_func = hist.get("personal_por_funcion") or actual.get("personal_por_funcion") or []
    por_loc = hist.get("personal_por_localidad") or actual.get("personal_por_localidad") or []
    loc_total = sum(int(x.get("valor") or 0) for x in por_loc) or 1

    equipos = hist.get("equipos_demanda") or []
    horas_u = hist.get("horas_por_unidad") or []
    tipos = hist.get("tareas_por_tipo") or []
    clases_t = hist.get("tareas_por_clase") or []
    horas_c = hist.get("horas_por_clase") or []
    anual = hist.get("ordenes_por_mes") or []
    mensual = actual.get("ordenes_por_mes") or []
    gente = actual.get("gente_ordenes_por_mes") or []

    # matriz mensual simple: meses x total
    matrix_rows = []
    if mensual:
        matrix_rows.append(
            {
                "label": "Órdenes",
                "cells": [_fmt(m.get("total")) for m in mensual[:12]],
            }
        )
    if gente:
        matrix_rows.append(
            {
                "label": "Personal",
                "cells": [_fmt(m.get("personal")) for m in gente[:12]],
            }
        )

    proximas = sorted(
        [it for it in (vtv.get("items") or [])],
        key=lambda x: x.get("dias", 9999),
    )[:6]

    plan_rows = sorted(
        [
            {
                "label": f.get("codigo") or f.get("nombre") or "—",
                "value": f.get("cumplimiento") or 0,
            }
            for f in (plan.get("filas") or [])
            if (f.get("tot_p") or 0) > 0
        ],
        key=lambda x: x["value"],
    )

    top1 = equipos[0] if equipos else None
    slides = [
        {
            "tags": ["reporte_mensual", "plan", "vtv", "importar"],
            "layout": "circuit",
            "eyebrow": "CIRCUITO INTEGRAL DE MANTENIMIENTO",
            "title": "Especialidades que sostienen la disponibilidad de flota",
            "highlight": "disponibilidad de flota",
            "cards": circuit_cards
            or [
                {"letter": "M", "title": "Mecánica", "text": "Correctivo y preventivo de flota.", "accent": "dark"},
                {"letter": "S", "title": "Soldadura", "text": "Fabricación y reparación estructural.", "accent": "green"},
                {"letter": "E", "title": "Eléctrico", "text": "Diagnóstico e instrumentación / VTV.", "accent": "dark"},
                {"letter": "L", "title": "Logística", "text": "Traslados y coordinación de bases.", "accent": "gold"},
            ],
            "dark_bar": {
                "left": "NEUQUÉN  →  CATRIEL  ·  BASES Y FRENTES",
                "metrics": [
                    {"value": _fmt(len(personal) or hk.get("personal")), "label": "personas en el equipo"},
                    {"value": _fmt(hk.get("unidades_con_orden")), "label": "unidades de flota"},
                    {"value": _fmt(len(por_loc) or 2), "label": "bases / localidades"},
                ],
            },
            "footer": "MECÁNICA · SOLDADURA · ELÉCTRICO · LOGÍSTICA",
        },
        {
            "tags": ["reporte_mensual"],
            "layout": "kpi_bars",
            "eyebrow": f"INDICADORES DE MANTENIMIENTO · {periodo}",
            "title": "Volumen histórico de órdenes y mix de tareas",
            "highlight": "mix de tareas",
            "kpis": [
                {"value": _fmt(hk.get("ordenes")), "label": "órdenes históricas", "tone": "dark"},
                {"value": _fmt(hk.get("tareas")), "label": "tareas históricas", "tone": "gold"},
                {"value": _fmt(hk.get("horas")), "label": "horas hombre", "tone": "green"},
                {"value": _fmt(hk.get("unidades_con_orden")), "label": "unidades", "tone": "white"},
            ],
            "bars": [
                {
                    "label": a.get("label") or str(a.get("anio") or ""),
                    "value": _fmt(a.get("total")),
                    "pct": _bar_pct(a.get("total"), anual, "total"),
                }
                for a in anual
            ],
            "bars_title": "ÓRDENES POR AÑO",
            "note": "Serie histórica consolidada desde la base de mantenimiento GOS.",
            "footer": "VOLUMEN HISTÓRICO",
        },
        {
            "tags": ["reporte_mensual"],
            "layout": "ranking_spotlight",
            "eyebrow": f"GESTIÓN DE FLOTA · {periodo}",
            "title": "Las unidades con mayor demanda concentran las intervenciones",
            "highlight": "mayor demanda",
            "kpis": [
                {"value": _fmt(hk.get("unidades_con_orden")), "label": "unidades distintas", "tone": "dark"},
                {"value": _fmt(hk.get("tareas")), "label": "tareas totales", "tone": "gold"},
                {"value": _fmt(hk.get("ordenes")), "label": "órdenes emitidas", "tone": "green"},
                {
                    "value": _fmt(top1.get("valor")) if top1 else "—",
                    "label": f"líder · {top1.get('label')}" if top1 else "líder",
                    "tone": "white",
                },
            ],
            "ranking": _rank(equipos, limit=10),
            "ranking_title": "TOP 10 POR ÓRDENES",
            "spotlight": {
                "value": _fmt(top1.get("valor")) if top1 else "—",
                "text": (
                    f"{top1.get('label')} concentra la mayor cantidad de órdenes del período."
                    if top1
                    else "Sin datos de equipos."
                ),
            },
            "note": f"Período consolidado {periodo}. Ranking por órdenes distintas sobre unidad.",
            "footer": "TOP 10 POR ÓRDENES",
        },
        {
            "tags": ["reporte_mensual"],
            "layout": "ranking",
            "eyebrow": f"HORAS POR UNIDAD · {periodo}",
            "title": "Carga de horas hombre sobre la flota crítica",
            "highlight": "flota crítica",
            "ranking": _rank(horas_u, limit=10),
            "ranking_title": "TOP 10 POR HORAS",
            "footer": "HORAS POR UNIDAD",
        },
        {
            "tags": ["vtv", "reporte_mensual"],
            "layout": "team_vtv",
            "eyebrow": "INDICADORES DEL EQUIPO Y CUMPLIMIENTO LEGAL",
            "title": "El equipo combina especialización técnica y cobertura territorial",
            "highlight": "cobertura territorial",
            "oficios": [
                {
                    "label": x.get("label") or "—",
                    "value": int(x.get("valor") or 0),
                    "pct": (int(x.get("valor") or 0) / max(1, sum(int(i.get("valor") or 0) for i in por_func))),
                }
                for x in por_func[:8]
            ],
            "bases": [
                {
                    "label": x.get("label") or "—",
                    "value": int(x.get("valor") or 0),
                    "pct": int(x.get("valor") or 0) / loc_total,
                    "text": f"{_fmt(x.get('valor'))} personas · {_pct(100 * int(x.get('valor') or 0) / loc_total)}",
                }
                for x in por_loc
            ],
            "team_total": len(personal) or int(hk.get("personal") or 0),
            "vtv_kpis": [
                {"value": _fmt(vk.get("vencidas")), "label": f"vencidas ({_fmt(vk.get('total'))} controladas)"},
            ],
            "vtv_rows": [
                {
                    "a": it.get("codigo") or it.get("nombre") or "—",
                    "b": it.get("vencimiento") or "—",
                    "c": f'{it.get("dias", "—")} días',
                }
                for it in proximas
            ],
            "footer": "EQUIPO · COBERTURA · CUMPLIMIENTO",
        },
        {
            "tags": ["reporte_mensual"],
            "layout": "category_board",
            "eyebrow": f"TABLERO DE CATEGORÍAS · {periodo}",
            "title": "Tareas y horas invertidas por especialidad / clase",
            "highlight": "especialidad / clase",
            "categories": [
                {
                    "title": c.get("label") or "—",
                    "value": _fmt(c.get("valor")),
                    "sub": next(
                        (
                            f"{_fmt(h.get('valor'))} hs  ·  tareas / horas"
                            for h in horas_c
                            if (h.get("label") or "").upper() == (c.get("label") or "").upper()
                        ),
                        "tareas registradas",
                    ),
                }
                for c in clases_t[:8]
            ],
            "footer": "TABLERO DE CATEGORÍAS",
        },
        {
            "tags": ["reporte_mensual"],
            "layout": "kpi_bars",
            "eyebrow": f"EVOLUCIÓN POR TIPO DE TAREA · {periodo}",
            "title": "El correctivo predomina; preventivo y legal sostienen el control",
            "highlight": "preventivo y legal",
            "kpis": [
                {
                    "value": _fmt(next((t.get("valor") for t in tipos if "CORRECT" in (t.get("label") or "").upper()), 0)),
                    "label": "correctivo",
                    "tone": "dark",
                },
                {
                    "value": _fmt(next((t.get("valor") for t in tipos if "PREVEN" in (t.get("label") or "").upper()), 0)),
                    "label": "preventivo",
                    "tone": "gold",
                },
                {
                    "value": _fmt(next((t.get("valor") for t in tipos if "LEGAL" in (t.get("label") or "").upper()), 0)),
                    "label": "legal / VTV",
                    "tone": "green",
                },
                {
                    "value": _fmt(next((t.get("valor") for t in tipos if "FABRIC" in (t.get("label") or "").upper()), 0)),
                    "label": "fabricación",
                    "tone": "white",
                },
            ],
            "bars": [
                {
                    "label": t.get("label") or "—",
                    "value": _fmt(t.get("valor")),
                    "pct": _bar_pct(t.get("valor"), tipos),
                }
                for t in tipos[:8]
            ],
            "bars_title": "DISTRIBUCIÓN POR TIPO",
            "footer": "EVOLUCIÓN POR TIPO",
        },
        {
            "tags": ["reporte_mensual"],
            "layout": "matrix",
            "eyebrow": f"COMPORTAMIENTO MENSUAL · {anio_actual}",
            "title": "La carga mensual varía según la demanda operativa",
            "highlight": "demanda operativa",
            "headers": [m.get("label") or str(m.get("mes") or "") for m in mensual[:12]],
            "rows": matrix_rows,
            "callouts": _month_callouts(mensual),
            "footer": f"DEMANDA MENSUAL {anio_actual}",
        },
        {
            "tags": ["plan"],
            "layout": "kpi_rank",
            "eyebrow": f"PLAN PREVENTIVO · {plan.get('anio') or anio_actual}",
            "title": "Cumplimiento del plan preventivo por unidad",
            "highlight": "plan preventivo",
            "kpis": [
                {"value": _pct(pk.get("cumplimiento"), ratio=True), "label": "cumplimiento global", "tone": "gold"},
                {"value": _fmt(pk.get("programado")), "label": "programado", "tone": "dark"},
                {"value": _fmt(pk.get("ejecutado")), "label": "ejecutado", "tone": "green"},
                {"value": _fmt(pk.get("unidades")), "label": "unidades en plan", "tone": "white"},
            ],
            "ranking": [
                {
                    "rank": f"{i:02d}",
                    "label": r["label"],
                    "value": _pct(r["value"], ratio=True),
                }
                for i, r in enumerate(plan_rows[:10], 1)
            ],
            "ranking_title": "UNIDADES CON MENOR CUMPLIMIENTO",
            "bars": [
                {
                    "label": m.get("label") or str(m.get("mes")),
                    "value": _pct(m.get("cumplimiento"), ratio=True) if m.get("cuenta_en_c") else "—",
                    "pct": float(m.get("cumplimiento") or 0) if m.get("cuenta_en_c") else 0,
                }
                for m in (plan.get("por_mes") or [])[:12]
            ],
            "bars_title": "CUMPLIMIENTO MENSUAL DEL PLAN",
            "note": "Cumplimiento = ejecutado / programado sobre meses ya alcanzados.",
            "footer": "PLAN PREVENTIVO",
        },
        {
            "tags": ["vtv"],
            "layout": "kpi_rows",
            "eyebrow": "VTV — CONTROL LEGAL DE FLOTA",
            "title": "Habilitación legal y próximos vencimientos",
            "highlight": "próximos vencimientos",
            "kpis": [
                {"value": _fmt(vk.get("vencidas")), "label": "vencidas", "tone": "dark"},
                {"value": _fmt(vk.get("por_vencer")), "label": "por vencer", "tone": "gold"},
                {"value": _fmt(vk.get("vigentes")), "label": "vigentes", "tone": "green"},
                {"value": _fmt(vk.get("programadas")), "label": "turnos programados", "tone": "white"},
            ],
            "rows": [
                {
                    "a": it.get("codigo") or it.get("nombre") or "—",
                    "b": it.get("vencimiento") or "—",
                    "c": f'{it.get("dias", "—")} días · {it.get("estado", "")}',
                }
                for it in proximas
            ],
            "rows_title": "Agenda de vencimientos",
            "footer": "VTV",
        },
        {
            "tags": ["plan", "vtv", "reporte_mensual", "importar"],
            "layout": "next_steps",
            "eyebrow": "PRÓXIMOS PASOS",
            "title": "Compromisos para fortalecer la disponibilidad de la flota",
            "highlight": "disponibilidad de la flota",
            "steps": [
                {
                    "n": "01",
                    "title": "Consolidar el tablero integral",
                    "text": "Tareas, órdenes, VTV y plan preventivo en una vista.",
                },
                {
                    "n": "02",
                    "title": "Elevar el cumplimiento del plan",
                    "text": f"Hoy {_pct(pk.get('cumplimiento'), ratio=True)} de avance sobre lo programado.",
                },
                {
                    "n": "03",
                    "title": "Anticipar alertas de VTV",
                    "text": f"{_fmt(vk.get('por_vencer'))} unidades por vencer · {_fmt(vk.get('vencidas'))} vencidas.",
                },
                {
                    "n": "04",
                    "title": "Reducir concentración en flota crítica",
                    "text": (
                        f"Priorizar {top1.get('label')} y el top de demanda."
                        if top1
                        else "Revisar unidades con mayor intervención."
                    ),
                },
                {
                    "n": "05",
                    "title": "Balancear correctivo / preventivo",
                    "text": "Subir la participación del preventivo sobre el correctivo.",
                },
                {
                    "n": "06",
                    "title": "Revisar resultados trimestralmente",
                    "text": "Con Operaciones y Abastecimiento.",
                },
            ],
            "footer": "COMPROMISOS DE GESTIÓN",
        },
        {
            "tags": ["reporte_mensual", "importar"],
            "layout": "team_roster",
            "eyebrow": "EQUIPO ACTUAL DE MANTENIMIENTO",
            "title": "Personas que sostienen la disponibilidad de la flota",
            "highlight": "disponibilidad de la flota",
            "people": [
                {
                    "nombre": p.get("nombre") or "—",
                    "rol": p.get("funcion") or p.get("funcion_general") or "—",
                    "base": p.get("localidad_real") or "—",
                }
                for p in personal[:16]
            ],
            "note": f"{len(personal) or hk.get('personal') or 0} personas sostienen la disponibilidad de la flota.",
            "footer": "GREEN OIL SERVICES",
        },
    ]

    return {
        "periodo": periodo,
        "overview_kpis": overview,
        "chips": ["Órdenes", "Tareas", "Unidades", "Personal", "VTV"],
        "slides": slides,
    }


def _month_callouts(mensual: list[dict]) -> list[dict]:
    if not mensual:
        return []
    ranked = sorted(mensual, key=lambda m: -(m.get("total") or 0))
    out = []
    if ranked:
        m = ranked[0]
        out.append({"title": m.get("label") or "", "text": f"pico de órdenes ({_fmt(m.get('total'))})"})
    if len(ranked) > 1:
        m = ranked[1]
        out.append({"title": m.get("label") or "", "text": f"segunda carga ({_fmt(m.get('total'))})"})
    if len(ranked) > 2:
        m = ranked[-1]
        out.append({"title": m.get("label") or "", "text": f"menor carga ({_fmt(m.get('total'))})"})
    return out[:3]


# ── Otros módulos (multi-slide con datos) ───────────────────────────────────


def _pack_capacitacion() -> dict:
    from gos.modulos.capacitacion.services.dashboard_service import resumen_dashboard

    eid = _empresa_id()
    if not eid:
        return {}
    data = resumen_dashboard(eid) or {}
    k = data.get("kpis") or {}
    personas = data.get("cumplimiento_por_persona") or []
    cursos = data.get("ranking_vencimientos") or []
    tipos = data.get("cumplimiento_por_tipo") or []
    sectores = data.get("cumplimiento_por_sector") or []
    evo = data.get("evolucion_mensual") or []

    overview = [
        {"value": _fmt(k.get("personas_activas")), "label": "personas activas"},
        {"value": _pct(k.get("cumplimiento_general")), "label": "cumplimiento general"},
        {"value": _fmt(k.get("vencidas")), "label": "vencidas"},
        {"value": _fmt(k.get("cursos_cargados")), "label": "cursos cargados"},
    ]
    slides = [
        {
            "tags": ["dashboard", "matriz", "personas", "programas", "catalogos", "reportes", "alertas", "cronograma", "configuracion"],
            "layout": "kpi_bars",
            "eyebrow": "CAPACITACIÓN · ESTADO GENERAL",
            "title": "Cumplimiento, pendientes y ejecución del mes",
            "highlight": "ejecución del mes",
            "kpis": [
                {"value": _fmt(k.get("personas_activas")), "label": "activas", "tone": "dark"},
                {"value": _pct(k.get("cumplimiento_general")), "label": "cumplimiento", "tone": "gold"},
                {"value": _fmt(k.get("pendientes")), "label": "pendientes", "tone": "green"},
                {"value": _fmt(k.get("encuentros_mes")), "label": "encuentros mes", "tone": "white"},
            ],
            "bars": [
                {"label": t.get("nombre") or t.get("tipo") or "—", "value": _pct(t.get("pct")), "pct": (t.get("pct") or 0) / 100}
                for t in tipos[:8]
            ],
            "bars_title": "CUMPLIMIENTO POR TIPO",
            "footer": "DASHBOARD",
        },
        {
            "tags": ["matriz", "personas"],
            "layout": "ranking",
            "eyebrow": "MATRIZ ANALÍTICA",
            "title": "Personas con mayor brecha de formación",
            "highlight": "brecha de formación",
            "ranking": [
                {"rank": f"{i:02d}", "label": p.get("nombre") or "—", "value": f'{p.get("pct", "—")}% · {p.get("pendientes", 0)} pend.'}
                for i, p in enumerate(personas[:10], 1)
            ],
            "ranking_title": "MENOR CUMPLIMIENTO",
            "footer": "MATRIZ",
        },
        {
            "tags": ["catalogos", "alertas", "reportes"],
            "layout": "ranking_spotlight",
            "eyebrow": "VENCIMIENTOS",
            "title": "Cursos con más vencimientos activos",
            "highlight": "vencimientos activos",
            "kpis": [
                {"value": _fmt(k.get("vencidas")), "label": "vencidas", "tone": "dark"},
                {"value": _fmt(k.get("proximas_vencer")), "label": "próximas", "tone": "gold"},
                {"value": _fmt(k.get("obligatorias_pendientes")), "label": "obligatorias pend.", "tone": "green"},
                {"value": _pct(data.get("habilitados_pct")), "label": "habilitados", "tone": "white"},
            ],
            "ranking": [
                {"rank": f"{i:02d}", "label": c.get("nombre") or c.get("codigo") or "—", "value": _fmt(c.get("count"))}
                for i, c in enumerate(cursos[:10], 1)
            ],
            "ranking_title": "TOP CURSOS POR VENCIMIENTOS",
            "spotlight": {
                "value": _fmt(cursos[0].get("count")) if cursos else "—",
                "text": f"{(cursos[0].get('nombre') if cursos else 'Sin datos')} encabeza el ranking de vencimientos.",
            },
            "footer": "ALERTAS · CATÁLOGO",
        },
        {
            "tags": ["cronograma", "programas", "dashboard"],
            "layout": "kpi_bars",
            "eyebrow": "CRONOGRAMA Y EJECUCIÓN",
            "title": "Evolución mensual de capacitaciones realizadas",
            "highlight": "realizadas",
            "kpis": [
                {"value": _fmt(k.get("realizadas_mes")), "label": "realizadas mes", "tone": "dark"},
                {"value": _fmt(k.get("horas_hombre_mes")), "label": "horas hombre mes", "tone": "gold"},
                {"value": _pct(k.get("tasa_aprobacion")), "label": "aprobación", "tone": "green"},
                {"value": _fmt(k.get("encuentros_mes")), "label": "encuentros", "tone": "white"},
            ],
            "bars": [
                {"label": e.get("mes") or "—", "value": _fmt(e.get("realizadas")), "pct": _bar_pct(e.get("realizadas"), [{"valor": x.get("realizadas")} for x in evo])}
                for e in evo
            ],
            "bars_title": "REALIZADAS POR MES",
            "footer": "CRONOGRAMA",
        },
        {
            "tags": ["reportes", "dashboard"],
            "layout": "ranking",
            "eyebrow": "SECTORES",
            "title": "Cumplimiento por sector",
            "highlight": "por sector",
            "ranking": [
                {"rank": f"{i:02d}", "label": s.get("nombre") or "—", "value": _pct(s.get("pct"))}
                for i, s in enumerate(sorted(sectores, key=lambda x: -(x.get("pct") or 0))[:10], 1)
            ],
            "ranking_title": "SECTORES",
            "footer": "REPORTES",
        },
    ]
    return {"periodo": str(date.today().year), "overview_kpis": overview, "chips": ["Personas", "Cursos", "Matriz", "Alertas", "ISO"], "slides": slides}


def _pack_vacaciones() -> dict:
    from gos.extensions import db
    from gos.modulos.vacaciones import services as vac

    session = db.session
    empleados = vac.get_empleados(session) or []
    sectores = vac.get_resumen_sector(session) or []
    try:
        tot = vac.get_tot_hs_resumen(session) or {}
    except Exception:
        tot = {}
    overview = [
        {"value": _fmt(len(empleados)), "label": "empleados"},
        {"value": _fmt(sum(int(s.get("pendientes") or 0) for s in sectores)), "label": "días pendientes"},
        {"value": _fmt(tot.get("total_horas")), "label": "horas Tot Hs."},
        {"value": _fmt(len(sectores)), "label": "sectores"},
    ]
    slides = [
        {
            "tags": ["adeudadas", "importar"],
            "layout": "ranking",
            "eyebrow": "VACACIONES ADEUDADAS",
            "title": "Días pendientes por sector",
            "highlight": "por sector",
            "ranking": [
                {"rank": f"{i:02d}", "label": s.get("sector") or "—", "value": f'{_fmt(s.get("pendientes"))} d · {s.get("personas", "—")} pers.'}
                for i, s in enumerate(sorted(sectores, key=lambda x: -(x.get("pendientes") or 0))[:10], 1)
            ],
            "ranking_title": "SECTORES",
            "footer": "ADEUDADAS",
        },
        {
            "tags": ["tot_hs", "importar"],
            "layout": "kpi_bars",
            "eyebrow": "TOT HS.",
            "title": "Control de horas y conceptos",
            "highlight": "horas y conceptos",
            "kpis": [
                {"value": _fmt(tot.get("total_horas")), "label": "total horas", "tone": "dark"},
                {"value": _fmt(tot.get("hs_extras")), "label": "hs extras", "tone": "gold"},
                {"value": _fmt(tot.get("vacaciones")), "label": "hs vacaciones", "tone": "green"},
                {"value": _fmt(tot.get("personas")), "label": "personas", "tone": "white"},
            ],
            "bars": [
                {"label": lab, "value": _fmt(tot.get(key)), "pct": _bar_pct(tot.get(key), [{"valor": tot.get(k)} for k in ("total_horas", "hs_extras", "vacaciones", "ausente", "enfermedad") if tot.get(k) is not None])}
                for lab, key in [("Total", "total_horas"), ("Extras", "hs_extras"), ("Vacaciones", "vacaciones"), ("Ausente", "ausente"), ("Enfermedad", "enfermedad")]
                if tot.get(key) is not None
            ],
            "bars_title": "CONCEPTOS",
            "footer": "TOT HS",
        },
    ]
    return {"overview_kpis": overview, "chips": ["Adeudadas", "Tot Hs.", "Sectores"], "slides": slides}


def _pack_ralenti() -> dict:
    from gos.modulos.ralenti import storage

    events = storage.list_events() or []
    by_veh: dict[str, float] = defaultdict(float)
    by_pers: dict[str, float] = defaultdict(float)
    litros = mins = 0.0
    for ev in events:
        m = float(ev.get("dur_min") or 0)
        l = float(ev.get("litros") or 0)
        mins += m
        litros += l
        by_veh[(ev.get("vehiculo") or "Sin unidad").strip() or "Sin unidad"] += m
        by_pers[(ev.get("persona") or "Sin persona").strip() or "Sin persona"] += m
    top_v = sorted(by_veh.items(), key=lambda x: -x[1])
    top_p = sorted(by_pers.items(), key=lambda x: -x[1])
    horas = mins / 60
    overview = [
        {"value": _fmt(len(events)), "label": "eventos"},
        {"value": _fmt(round(horas, 1)), "label": "horas ralentí"},
        {"value": _fmt(round(litros, 1)), "label": "litros"},
        {"value": _fmt(len(by_veh)), "label": "unidades"},
    ]
    slides = [
        {
            "tags": ["dashboard"],
            "layout": "ranking_spotlight",
            "eyebrow": "RALENTÍ POR UNIDAD",
            "title": "Unidades con mayor tiempo en ralentí",
            "highlight": "ralentí",
            "kpis": overview,
            "ranking": [{"rank": f"{i:02d}", "label": v, "value": f"{_fmt(round(m/60,1))} h"} for i, (v, m) in enumerate(top_v[:10], 1)],
            "ranking_title": "TOP UNIDADES",
            "spotlight": {
                "value": f"{_fmt(round(top_v[0][1]/60,1))} h" if top_v else "—",
                "text": f"{top_v[0][0]} concentra el mayor ralentí." if top_v else "Sin datos",
            },
            "footer": "UNIDADES",
        },
        {
            "tags": ["dashboard"],
            "layout": "ranking",
            "eyebrow": "RALENTÍ POR PERSONA",
            "title": "Personas con mayor acumulación de ralentí",
            "highlight": "ralentí",
            "ranking": [{"rank": f"{i:02d}", "label": p, "value": f"{_fmt(round(m/60,1))} h"} for i, (p, m) in enumerate(top_p[:10], 1)],
            "ranking_title": "TOP PERSONAS",
            "footer": "PERSONAS",
        },
    ]
    return {"overview_kpis": overview, "chips": ["Horas", "Litros", "Unidades"], "slides": slides}


def _pack_objetivos() -> dict:
    eid = _empresa_id()
    if not eid:
        return {}
    from gos.modulos.objetivos.services.foda_service import obtener_matriz
    from gos.modulos.objetivos.services.reportes_service import generar_informe_cumplimiento

    info = generar_informe_cumplimiento(eid)
    matriz = obtener_matriz(eid) or {}
    foda_counts = {k: len(v or []) for k, v in matriz.items()}
    objs = getattr(info, "objetivos", None) or []
    overview = [
        {"value": _fmt(getattr(info, "total_objetivos", None)), "label": "objetivos"},
        {"value": _fmt(getattr(info, "total_kpis", None)), "label": "KPI"},
        {"value": _pct(getattr(info, "pct_kpis_cumplidos", None)), "label": "KPI cumplidos"},
        {"value": _pct(getattr(info, "pct_objetivos_cumplidos", None)), "label": "objetivos ok"},
    ]
    slides = [
        {
            "tags": ["dashboard", "reportes", "kpi", "estrategicos", "foda", "configuracion"],
            "layout": "kpi_bars",
            "eyebrow": "PLANEAMIENTO ESTRATÉGICO",
            "title": "Cumplimiento agregado de objetivos e indicadores",
            "highlight": "objetivos e indicadores",
            "kpis": overview,
            "bars": [
                {"label": o.get("codigo") or o.get("nombre") or "—", "value": _pct(o.get("pct_cumplimiento")), "pct": (o.get("pct_cumplimiento") or 0) / 100}
                for o in sorted(objs, key=lambda x: -(x.get("pct_cumplimiento") or 0))[:8]
            ],
            "bars_title": "OBJETIVOS",
            "footer": "DASHBOARD",
        },
        {
            "tags": ["foda"],
            "layout": "category_board",
            "eyebrow": "FODA / DAFO",
            "title": "Composición del diagnóstico estratégico",
            "highlight": "diagnóstico estratégico",
            "categories": [
                {"title": "Fortalezas", "value": _fmt(foda_counts.get("F")), "sub": "factores internos positivos"},
                {"title": "Oportunidades", "value": _fmt(foda_counts.get("O")), "sub": "factores externos positivos"},
                {"title": "Debilidades", "value": _fmt(foda_counts.get("D")), "sub": "factores internos a mejorar"},
                {"title": "Amenazas", "value": _fmt(foda_counts.get("A")), "sub": "factores externos de riesgo"},
            ],
            "footer": "FODA",
        },
        {
            "tags": ["estrategicos", "kpi", "reportes"],
            "layout": "ranking",
            "eyebrow": "OBJETIVOS",
            "title": "Ranking de cumplimiento por objetivo",
            "highlight": "por objetivo",
            "ranking": [
                {"rank": f"{i:02d}", "label": o.get("codigo") or o.get("nombre") or "—", "value": _pct(o.get("pct_cumplimiento"))}
                for i, o in enumerate(sorted(objs, key=lambda x: -(x.get("pct_cumplimiento") or 0))[:10], 1)
            ],
            "ranking_title": "CUMPLIMIENTO",
            "footer": "OBJETIVOS",
        },
        {
            "tags": ["kpi", "reportes"],
            "layout": "kpi_rows",
            "eyebrow": "KPI",
            "title": "Estado de los indicadores del planeamiento",
            "highlight": "indicadores",
            "kpis": [
                {"value": _fmt(getattr(info, "kpis_cumplidos", None)), "label": "cumplidos", "tone": "dark"},
                {"value": _fmt(getattr(info, "kpis_fuera", None)), "label": "fuera de meta", "tone": "gold"},
                {"value": _fmt(getattr(info, "kpis_sin_datos", None)), "label": "sin datos", "tone": "green"},
                {"value": _pct(getattr(info, "pct_kpis_cumplidos", None)), "label": "% cumplimiento", "tone": "white"},
            ],
            "rows": [],
            "footer": "KPI",
        },
    ]
    return {"overview_kpis": overview, "chips": ["FODA", "Objetivos", "KPI", "Reportes"], "slides": slides}


def _pack_om() -> dict:
    from gos.modulos.om import services as om

    mods = om.list_modules(include_inactive=True) or []
    activos = [m for m in mods if (m.get("status") or "").lower() == "active"]
    pers = sum(len(m.get("personnel") or []) for m in mods)
    units = sum(len(m.get("units") or []) for m in mods)
    tools = sum(len(m.get("tools") or []) for m in mods)
    supplies = sum(len(m.get("supplies") or []) for m in mods)
    overview = [
        {"value": _fmt(len(mods)), "label": "módulos"},
        {"value": _fmt(len(activos)), "label": "activos"},
        {"value": _fmt(pers), "label": "personal"},
        {"value": _fmt(units), "label": "unidades"},
    ]
    slides = [
        {
            "tags": ["apertura"],
            "layout": "ranking_spotlight",
            "eyebrow": "APERTURA O&M",
            "title": "Dotación de personal y recursos por módulo",
            "highlight": "por módulo",
            "kpis": [
                {"value": _fmt(pers), "label": "personal", "tone": "dark"},
                {"value": _fmt(units), "label": "unidades", "tone": "gold"},
                {"value": _fmt(tools), "label": "herramientas", "tone": "green"},
                {"value": _fmt(supplies), "label": "insumos", "tone": "white"},
            ],
            "ranking": [
                {
                    "rank": f"{i:02d}",
                    "label": m.get("name") or m.get("code") or "—",
                    "value": f'{len(m.get("personnel") or [])}p · {len(m.get("units") or [])}u',
                }
                for i, m in enumerate(mods[:10], 1)
            ],
            "ranking_title": "MÓDULOS",
            "spotlight": {
                "value": _fmt(len(activos)),
                "text": f"{len(activos)} módulos activos de {len(mods)} totales.",
            },
            "footer": "APERTURA",
        }
    ]
    return {"overview_kpis": overview, "chips": ["Personal", "Unidades", "Herramientas", "Insumos"], "slides": slides}


def _pack_recursos() -> dict:
    from gos.modulos.recursos import services as rec

    data = rec.resumen()
    huecos = data.get("huecos") or []
    overview = [
        {"value": _fmt(data.get("unidades")), "label": "unidades"},
        {"value": _fmt(data.get("asignadas")), "label": "asignadas"},
        {"value": _fmt(data.get("faltantes")), "label": "faltantes"},
        {"value": _fmt(data.get("libres")), "label": "libres"},
    ]
    slides = [
        {
            "tags": ["tablero"],
            "layout": "ranking_spotlight",
            "eyebrow": "RECURSOS OPERACIÓN",
            "title": "La flota se afecta por servicio y estructura",
            "highlight": "por servicio y estructura",
            "kpis": [
                {"value": _fmt(data.get("unidades")), "label": "unidades", "tone": "dark"},
                {"value": _fmt(data.get("por_grupo", {}).get("servicio")), "label": "en servicio", "tone": "gold"},
                {"value": _fmt(data.get("faltantes")), "label": "faltantes", "tone": "green"},
                {"value": _fmt(data.get("sin_asignar")), "label": "sin asignar", "tone": "white"},
            ],
            "ranking": [
                {
                    "rank": f"{i:02d}",
                    "label": f'{h.get("destino") or "—"} · {h.get("tipo")}',
                    "value": _fmt(h.get("faltan")),
                }
                for i, h in enumerate(huecos[:10], 1)
            ],
            "ranking_title": "HUECOS",
            "spotlight": {
                "value": _fmt(data.get("faltantes")),
                "text": f"{data.get('faltantes') or 0} cupos sin cubrir en servicios y estructura.",
            },
            "footer": "TABLERO",
        }
    ]
    return {"overview_kpis": overview, "chips": ["Flota", "Servicios", "Cupos", "Estados"], "slides": slides}


def _pack_hwo() -> dict:
    from gos.modulos.hwo.storage import get_all_datasets

    datasets = get_all_datasets() or []
    rows = sum(int(d.get("row_count") or 0) for d in datasets)
    overview = [
        {"value": _fmt(len(datasets)), "label": "datasets"},
        {"value": _fmt(rows), "label": "filas totales"},
        {"value": _fmt(max((d.get("row_count") or 0) for d in datasets) if datasets else 0), "label": "mayor dataset"},
        {"value": "HWO", "label": "análisis"},
    ]
    slides = [
        {
            "tags": ["dashboard"],
            "layout": "ranking",
            "eyebrow": "ANÁLISIS HWO",
            "title": "Datasets cargados y volumen de registros",
            "highlight": "volumen de registros",
            "ranking": [
                {"rank": f"{i:02d}", "label": d.get("name") or "—", "value": _fmt(d.get("row_count"))}
                for i, d in enumerate(sorted(datasets, key=lambda x: -(x.get("row_count") or 0))[:10], 1)
            ],
            "ranking_title": "DATASETS",
            "footer": "DASHBOARD",
        }
    ]
    return {"overview_kpis": overview, "chips": ["Datasets", "Equipos", "Incidencias"], "slides": slides}


def _pack_dashboard() -> dict:
    eid = _empresa_id()
    if not eid:
        return {}
    from gos.modulos.dashboard.services import build_summary

    summary = build_summary(eid) or {}
    modules = summary.get("modules") or []
    overview = [
        {"value": _fmt(summary.get("modules_ok")), "label": "módulos ok"},
        {"value": _fmt(summary.get("modules_total")), "label": "módulos totales"},
        {"value": _fmt(summary.get("alerts")), "label": "alertas"},
        {"value": _fmt(summary.get("health")), "label": "health"},
    ]
    slides = [
        {
            "tags": ["command_center"],
            "layout": "ranking",
            "eyebrow": "COMMAND CENTER",
            "title": "Estado unificado de los módulos GOS",
            "highlight": "módulos GOS",
            "ranking": [
                {
                    "rank": f"{i:02d}",
                    "label": m.get("label") or m.get("code") or "—",
                    "value": f'score {m.get("score", "—")} · {m.get("alerts", 0)} alertas',
                }
                for i, m in enumerate(modules[:10], 1)
            ],
            "ranking_title": "MÓDULOS",
            "footer": "COMMAND CENTER",
        }
    ]
    return {"overview_kpis": overview, "chips": [m.get("label") for m in modules[:6] if m.get("label")], "slides": slides}
