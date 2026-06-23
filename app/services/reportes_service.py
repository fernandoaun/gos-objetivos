"""Informe de cumplimiento: objetivos estratégicos ↔ KPI."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from app.models.objetivo import Objetivo
from app.services import kpi_service, objetivo_service


def _codigo_objetivo_kpi(codigo_kpi: str, objetivo_codigo: str | None) -> str | None:
    if objetivo_codigo:
        return objetivo_codigo
    match = re.match(r"KPI-(\d+)-", codigo_kpi or "")
    if not match:
        return None
    return f"OE-{int(match.group(1)):02d}"


@dataclass
class KpiInforme:
    id: int
    codigo: str
    indicador: str
    estado: str
    avance_pct: float | None
    agregado: float | None


@dataclass
class ObjetivoInforme:
    codigo: str
    nombre: str
    total_kpis: int
    kpis_cumplidos: int
    kpis_fuera: int
    kpis_sin_datos: int
    pct_cumplimiento: float | None
    cumplido: bool
    registrado: bool
    kpis: list[KpiInforme] = field(default_factory=list)


@dataclass
class ResumenInforme:
    total_objetivos: int
    total_kpis: int
    kpis_cumplidos: int
    kpis_fuera: int
    kpis_sin_datos: int
    pct_kpis_cumplidos: float | None
    objetivos_con_kpis: int
    objetivos_cumplidos: int
    pct_objetivos_cumplidos: float | None
    objetivos: list[ObjetivoInforme] = field(default_factory=list)
    kpis_sin_objetivo: list[KpiInforme] = field(default_factory=list)


DASHBOARD_FILTROS: dict[str, tuple[str, str]] = {
    "objetivos": (
        "Objetivos estratégicos",
        "Listado completo de objetivos estratégicos registrados.",
    ),
    "kpis": (
        "KPI totales",
        "Todos los indicadores agrupados por objetivo estratégico.",
    ),
    "kpis-cumplimiento": (
        "Cumplimiento de KPI",
        "Indicadores agrupados según su estado de cumplimiento.",
    ),
    "objetivos-cumplimiento": (
        "Cumplimiento de objetivos",
        "Objetivos estratégicos agrupados según su nivel de cumplimiento.",
    ),
    "en-meta": (
        "KPI en meta",
        "Indicadores que alcanzan o superan la meta 2026.",
    ),
    "fuera-meta": (
        "KPI fuera de meta",
        "Indicadores por debajo de la meta 2026.",
    ),
    "sin-datos": (
        "KPI sin datos",
        "Indicadores sin valores cargados para calcular el avance.",
    ),
}


@dataclass
class KpiConObjetivo:
    objetivo_codigo: str | None
    objetivo_nombre: str | None
    kpi: KpiInforme


@dataclass
class GrupoDetalle:
    titulo: str
    estilo: str
    objetivos: list[ObjetivoInforme] = field(default_factory=list)
    kpis: list[KpiConObjetivo] = field(default_factory=list)


@dataclass
class VistaDetalle:
    filtro: str
    titulo: str
    descripcion: str
    total: int
    grupos: list[GrupoDetalle] = field(default_factory=list)

    @property
    def hay_datos(self) -> bool:
        return any(g.objetivos or g.kpis for g in self.grupos)


def _kpis_con_objetivo(
    informe: ResumenInforme,
    *,
    estado: str | None = None,
) -> list[KpiConObjetivo]:
    items: list[KpiConObjetivo] = []
    for obj in informe.objetivos:
        for kpi in obj.kpis:
            if estado is None or kpi.estado == estado:
                items.append(
                    KpiConObjetivo(
                        objetivo_codigo=obj.codigo,
                        objetivo_nombre=obj.nombre,
                        kpi=kpi,
                    )
                )
    for kpi in informe.kpis_sin_objetivo:
        if estado is None or kpi.estado == estado:
            items.append(
                KpiConObjetivo(
                    objetivo_codigo=None,
                    objetivo_nombre=None,
                    kpi=kpi,
                )
            )
    return items


def _agrupar_kpis_por_objetivo(kpis: list[KpiConObjetivo]) -> list[GrupoDetalle]:
    por_obj: dict[str, GrupoDetalle] = {}
    orden: list[str] = []

    for item in kpis:
        key = item.objetivo_codigo or "__sin_objetivo__"
        if key not in por_obj:
            titulo = (
                f"{item.objetivo_codigo} — {item.objetivo_nombre}"
                if item.objetivo_codigo
                else "Sin objetivo asociado"
            )
            por_obj[key] = GrupoDetalle(titulo=titulo, estilo="neutral", kpis=[])
            orden.append(key)
        por_obj[key].kpis.append(item)

    return [por_obj[k] for k in orden]


def preparar_vista_detalle(informe: ResumenInforme, filtro: str) -> VistaDetalle:
    if filtro not in DASHBOARD_FILTROS:
        raise ValueError(f"Filtro de dashboard inválido: {filtro}")

    titulo, descripcion = DASHBOARD_FILTROS[filtro]
    grupos: list[GrupoDetalle] = []

    if filtro == "objetivos":
        grupos = [
            GrupoDetalle(
                titulo="Todos los objetivos",
                estilo="neutral",
                objetivos=informe.objetivos,
            )
        ]
        total = informe.total_objetivos

    elif filtro == "kpis":
        kpis = _kpis_con_objetivo(informe)
        grupos = _agrupar_kpis_por_objetivo(kpis)
        total = informe.total_kpis

    elif filtro == "kpis-cumplimiento":
        grupos = [
            GrupoDetalle(
                titulo="En meta",
                estilo="ok",
                kpis=_kpis_con_objetivo(informe, estado="En meta"),
            ),
            GrupoDetalle(
                titulo="Fuera de meta",
                estilo="bad",
                kpis=_kpis_con_objetivo(informe, estado="Fuera de meta"),
            ),
            GrupoDetalle(
                titulo="Sin datos",
                estilo="muted",
                kpis=_kpis_con_objetivo(informe, estado="Sin datos"),
            ),
        ]
        total = informe.total_kpis

    elif filtro == "objetivos-cumplimiento":
        cumplidos: list[ObjetivoInforme] = []
        parciales: list[ObjetivoInforme] = []
        no_cumplidos: list[ObjetivoInforme] = []
        sin_kpi: list[ObjetivoInforme] = []
        for obj in informe.objetivos:
            if obj.total_kpis == 0:
                sin_kpi.append(obj)
            elif obj.cumplido:
                cumplidos.append(obj)
            elif obj.kpis_cumplidos > 0:
                parciales.append(obj)
            else:
                no_cumplidos.append(obj)
        grupos = [
            GrupoDetalle(titulo="Cumplidos", estilo="ok", objetivos=cumplidos),
            GrupoDetalle(titulo="Cumplimiento parcial", estilo="warn", objetivos=parciales),
            GrupoDetalle(titulo="No cumplidos", estilo="bad", objetivos=no_cumplidos),
            GrupoDetalle(titulo="Sin KPI asociados", estilo="muted", objetivos=sin_kpi),
        ]
        total = informe.total_objetivos

    elif filtro == "en-meta":
        kpis = _kpis_con_objetivo(informe, estado="En meta")
        grupos = _agrupar_kpis_por_objetivo(kpis)
        total = informe.kpis_cumplidos

    elif filtro == "fuera-meta":
        kpis = _kpis_con_objetivo(informe, estado="Fuera de meta")
        grupos = _agrupar_kpis_por_objetivo(kpis)
        total = informe.kpis_fuera

    else:  # sin-datos
        kpis = _kpis_con_objetivo(informe, estado="Sin datos")
        grupos = _agrupar_kpis_por_objetivo(kpis)
        total = informe.kpis_sin_datos

    return VistaDetalle(
        filtro=filtro,
        titulo=titulo,
        descripcion=descripcion,
        total=total,
        grupos=grupos,
    )


def _kpi_informe(fila: dict) -> KpiInforme:
    kpi = fila["kpi"]
    avance = fila.get("avance")
    return KpiInforme(
        id=kpi.id,
        codigo=kpi.codigo,
        indicador=kpi.indicador,
        estado=fila["estado"],
        avance_pct=round(avance * 100, 1) if avance is not None else None,
        agregado=fila.get("agregado"),
    )


def _resumen_objetivo(
    codigo: str,
    nombre: str,
    kpis_filas: list[dict],
    *,
    registrado: bool,
) -> ObjetivoInforme:
    kpis = [_kpi_informe(f) for f in kpis_filas]
    total = len(kpis)
    cumplidos = sum(1 for k in kpis if k.estado == "En meta")
    fuera = sum(1 for k in kpis if k.estado == "Fuera de meta")
    sin_datos = sum(1 for k in kpis if k.estado == "Sin datos")
    pct = round(cumplidos / total * 100, 1) if total else None
    cumplido = total > 0 and cumplidos == total
    return ObjetivoInforme(
        codigo=codigo,
        nombre=nombre,
        total_kpis=total,
        kpis_cumplidos=cumplidos,
        kpis_fuera=fuera,
        kpis_sin_datos=sin_datos,
        pct_cumplimiento=pct,
        cumplido=cumplido,
        registrado=registrado,
        kpis=kpis,
    )


def generar_informe_cumplimiento(empresa_id: int) -> ResumenInforme:
    objetivos: list[Objetivo] = objetivo_service.listar_objetivos(empresa_id)
    kpis_filas = kpi_service.listar_kpis_con_metricas(empresa_id)

    por_objetivo: dict[str, list[dict]] = defaultdict(list)
    sin_objetivo: list[dict] = []

    for fila in kpis_filas:
        kpi = fila["kpi"]
        cod_oe = _codigo_objetivo_kpi(kpi.codigo, kpi.objetivo_codigo)
        if cod_oe:
            por_objetivo[cod_oe].append(fila)
        else:
            sin_objetivo.append(fila)

    objetivos_map = {o.codigo: o for o in objetivos}
    filas: list[ObjetivoInforme] = []
    codigos_incluidos: set[str] = set()

    for obj in objetivos:
        codigos_incluidos.add(obj.codigo)
        filas.append(
            _resumen_objetivo(
                obj.codigo,
                obj.nombre,
                por_objetivo.get(obj.codigo, []),
                registrado=True,
            )
        )

    for cod_oe, kpis_obj in sorted(por_objetivo.items()):
        if cod_oe in codigos_incluidos:
            continue
        filas.append(
            _resumen_objetivo(
                cod_oe,
                f"Objetivo {cod_oe} (sin registrar en el sistema)",
                kpis_obj,
                registrado=False,
            )
        )

    filas.sort(key=lambda item: item.codigo)

    total_kpis = len(kpis_filas)
    kpis_cumplidos = sum(1 for f in kpis_filas if f["estado"] == "En meta")
    kpis_fuera = sum(1 for f in kpis_filas if f["estado"] == "Fuera de meta")
    kpis_sin_datos = sum(1 for f in kpis_filas if f["estado"] == "Sin datos")
    pct_kpis = round(kpis_cumplidos / total_kpis * 100, 1) if total_kpis else None

    con_kpis = [o for o in filas if o.total_kpis > 0]
    objetivos_cumplidos = sum(1 for o in con_kpis if o.cumplido)
    pct_obj = (
        round(objetivos_cumplidos / len(con_kpis) * 100, 1) if con_kpis else None
    )

    return ResumenInforme(
        total_objetivos=len(objetivos),
        total_kpis=total_kpis,
        kpis_cumplidos=kpis_cumplidos,
        kpis_fuera=kpis_fuera,
        kpis_sin_datos=kpis_sin_datos,
        pct_kpis_cumplidos=pct_kpis,
        objetivos_con_kpis=len(con_kpis),
        objetivos_cumplidos=objetivos_cumplidos,
        pct_objetivos_cumplidos=pct_obj,
        objetivos=filas,
        kpis_sin_objetivo=[_kpi_informe(f) for f in sin_objetivo],
    )
