"""Exportación de datos de capacitaciones a Excel."""

from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill

from gos.modulos.capacitacion.services.matriz_analitica_service import (
    MESES_NOMBRES,
    matriz_analitica,
)
from gos.modulos.capacitacion.services.matriz_service import matriz_capacitaciones

_HEADER_FILL = PatternFill(start_color="1B4332", end_color="1B4332", fill_type="solid")
_HEADER_FONT = Font(color="FFFFFF", bold=True)
_LEGACY_COLOR_MAP = {
    "verde": "C6EFCE",
    "amarillo": "FFEB9C",
    "rojo": "FFC7CE",
    "azul": "BDD7EE",
    "gris": "D9D9D9",
}

_CAL_COLS = [
    ("programados", "Cursos Programados"),
    ("pendientes", "Cursos Pendientes"),
    ("cumplidos", "Cursos Cumplidos"),
    ("pct_cumpl_prog", "% Cumpl./Pr."),
    ("puntuales", "Cumplidos Puntuales"),
    ("pct_punt_prog", "% Punt./Pr."),
    ("pend_vencidos", "Pendientes Vencidos"),
    ("pct_venc_prog", "% Venc./Pr."),
]
_CAL_PCT_COLS = [
    ("pct_pend_sin_vencer", "Pendientes Sin Vencer"),
    ("pct_pend_vencidos", "Pendientes Vencidos"),
    ("pct_cumpl_puntuales", "Cumplidos Puntuales"),
    ("pct_cumpl_no_puntuales", "Cumplidos No Puntuales"),
]

_TABLA_SUB = ("prog", "pdtes", "cumpl", "cumpl_prog")
_TABLA_SUB_LABELS = ("Prog", "Pdtes", "Cumpl", "Cumpl/Prog")


def _write_header(ws, headers: list[str]) -> None:
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT


def _fmt_pct(val) -> str | float | int:
    if val is None:
        return ""
    if isinstance(val, float) and 0 <= val <= 1:
        return round(val * 100, 1)
    return val


def exportar_matriz_excel(empresa_id: int, **filtros) -> BytesIO:
    """Exportación legacy (persona × curso)."""
    data = matriz_capacitaciones(empresa_id, **filtros)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Matriz capacitaciones"

    headers = ["Persona", "Legajo", "Sector"] + [c["codigo"] for c in data["columnas"]]
    _write_header(ws, headers)

    for row_idx, fila in enumerate(data["filas"], 2):
        ws.cell(row=row_idx, column=1, value=fila["nombre"])
        ws.cell(row=row_idx, column=2, value=fila.get("legajo") or "")
        ws.cell(row=row_idx, column=3, value=fila.get("sector_nombre") or "")
        for col_idx, col in enumerate(data["columnas"], 4):
            celda = fila["celdas"].get(str(col["id"]), {})
            estado = celda.get("estado", "no_aplica")
            cell = ws.cell(row=row_idx, column=col_idx, value=estado)
            fill_color = _LEGACY_COLOR_MAP.get(celda.get("color", "gris"), "D9D9D9")
            cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _export_calendario_resumen(ws, data: dict) -> None:
    ws.title = "Capacitaciones"
    anio = data.get("anio", "")
    ws.cell(row=1, column=1, value="Programas")
    ws.cell(row=2, column=1, value="Planes")
    ws.cell(row=3, column=1, value="Personas")

    row_head = 4
    ws.cell(row=row_head, column=1, value=anio)
    col = 2
    for _, label in _CAL_COLS:
        ws.cell(row=row_head, column=col, value=label)
        col += 1
    for _, label in _CAL_PCT_COLS:
        ws.cell(row=row_head, column=col, value=label)
        col += 1

    all_cols = _CAL_COLS + _CAL_PCT_COLS
    for i, fila in enumerate(data.get("filas") or [], start=row_head + 1):
        ws.cell(row=i, column=1, value=fila.get("nombre"))
        for j, (key, _) in enumerate(all_cols, start=2):
            ws.cell(row=i, column=j, value=_fmt_pct(fila.get(key)))

    tot = data.get("totales") or {}
    row_tot = row_head + 1 + len(data.get("filas") or [])
    ws.cell(row=row_tot, column=1, value="Total")
    for j, (key, _) in enumerate(all_cols, start=2):
        ws.cell(row=row_tot, column=j, value=_fmt_pct(tot.get(key)))


def _export_tabla_personas(ws, data: dict) -> None:
    ws.title = "Capacitaciones"
    anio = data.get("anio", "")
    agrupar = data.get("agrupar_por", "persona")
    meses = data.get("meses") or [{"num": i, "nombre": n} for i, n in enumerate(MESES_NOMBRES, start=1)]

    ws.cell(row=1, column=1, value="Planes:")
    ws.cell(row=2, column=1, value="Puestos" if agrupar == "puesto" else "Personas")

    row_mes = 3
    row_sub = 4
    ws.cell(row=row_sub, column=1, value=anio)

    col = 2
    for mes in meses:
        ws.cell(row=row_mes, column=col, value=mes.get("nombre"))
        for j, sub in enumerate(_TABLA_SUB_LABELS):
            ws.cell(row=row_sub, column=col + j, value=sub)
        col += 4

    ws.cell(row=row_mes, column=col, value="Anual")
    for j, sub in enumerate(_TABLA_SUB_LABELS):
        ws.cell(row=row_sub, column=col + j, value=sub)

    for row_idx, fila in enumerate(data.get("filas") or [], start=row_sub + 1):
        ws.cell(row=row_idx, column=1, value=fila.get("nombre") or fila.get("persona"))
        meses_data = fila.get("meses") or {}
        col = 2
        for mes in meses:
            m = meses_data.get(str(mes["num"]), {})
            for j, sub in enumerate(_TABLA_SUB):
                ws.cell(row=row_idx, column=col + j, value=_fmt_pct(m.get(sub)))
            col += 4
        anual = meses_data.get("anual", {})
        for j, sub in enumerate(_TABLA_SUB):
            ws.cell(row=row_idx, column=col + j, value=_fmt_pct(anual.get(sub)))


def exportar_matriz_analitica_excel(
    empresa_id: int,
    *,
    vista: str = "tabla",
    anio: int | None = None,
    plan_ids=None,
    tipos=None,
    empresas=None,
    persona_ids=None,
    puesto_ids=None,
    persona_id: int | None = None,
    agrupar_por: str = "persona",
) -> BytesIO:
    """Exporta la matriz analítica según la vista activa."""
    result = matriz_analitica(
        empresa_id,
        vista=vista,
        anio=anio,
        plan_ids=plan_ids,
        tipos=tipos,
        empresas=empresas,
        persona_ids=persona_ids,
        puesto_ids=puesto_ids,
        persona_id=persona_id,
        agrupar_por=agrupar_por,
    )
    data = result["data"]
    wb = openpyxl.Workbook()
    ws = wb.active

    if vista in ("calendar", "calendario"):
        _export_calendario_resumen(ws, data)
    elif vista in ("person", "persona"):
        ws.title = "Persona"
        persona = data.get("persona") or {}
        headers = [
            "Programa",
            "Plan",
            "Curso",
            "Estado",
            "Nota",
            "Horas",
            "Empresa dictada",
            "Vencimiento",
        ]
        _write_header(ws, headers)
        row_idx = 2
        for prog in data.get("programas") or []:
            for curso in prog.get("cursos") or []:
                ws.cell(row=row_idx, column=1, value=prog.get("nombre"))
                ws.cell(row=row_idx, column=2, value=prog.get("plan_nombre"))
                ws.cell(row=row_idx, column=3, value=curso.get("nombre"))
                ws.cell(row=row_idx, column=4, value=curso.get("estado"))
                ws.cell(row=row_idx, column=5, value=curso.get("nota"))
                ws.cell(row=row_idx, column=6, value=curso.get("horas"))
                ws.cell(row=row_idx, column=7, value=curso.get("empresa"))
                ws.cell(row=row_idx, column=8, value=curso.get("fecha_vencimiento"))
                row_idx += 1
        if row_idx == 2:
            ws.cell(row=2, column=1, value=persona.get("nombre"))
    else:
        _export_tabla_personas(ws, data)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
