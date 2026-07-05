"""Exportación de datos de capacitaciones a Excel."""

from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill

from gos.modulos.capacitacion.services.matriz_analitica_service import matriz_analitica
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


def _write_header(ws, headers: list[str]) -> None:
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT


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
    )
    data = result["data"]
    wb = openpyxl.Workbook()
    ws = wb.active

    if vista in ("calendar", "calendario"):
        ws.title = "Calendario"
        headers = [
            "Fecha",
            "Curso",
            "Plan",
            "Tipo",
            "Empresa",
            "Estado",
            "Capacitador",
            "Lugar",
            "Personas",
        ]
        _write_header(ws, headers)
        row_idx = 2
        for mes in range(1, 13):
            for ev in (data.get("meses") or {}).get(mes, []):
                ws.cell(row=row_idx, column=1, value=ev.get("fecha"))
                ws.cell(row=row_idx, column=2, value=ev.get("curso_nombre"))
                ws.cell(row=row_idx, column=3, value=ev.get("plan_nombre"))
                ws.cell(row=row_idx, column=4, value=ev.get("tipo"))
                ws.cell(row=row_idx, column=5, value=ev.get("empresa_nombre"))
                ws.cell(row=row_idx, column=6, value=ev.get("estado"))
                ws.cell(row=row_idx, column=7, value=ev.get("capacitador"))
                ws.cell(row=row_idx, column=8, value=ev.get("lugar"))
                ws.cell(row=row_idx, column=9, value=ev.get("personas_count"))
                row_idx += 1
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
                ws.cell(row=row_idx, column=7, value=curso.get("empresa_dictada"))
                ws.cell(row=row_idx, column=8, value=curso.get("fecha_vencimiento"))
                row_idx += 1
        if row_idx == 2:
            ws.cell(row=2, column=1, value=persona.get("nombre"))
    else:
        ws.title = "Matriz tabla"
        headers = [
            "Programa",
            "Plan",
            "Curso",
            "Persona",
            "Puesto",
            "Estado",
            "Nota",
            "Horas acreditadas",
            "Vencimiento",
        ]
        _write_header(ws, headers)
        row_idx = 2
        for sec in data.get("secciones") or []:
            for curso in sec.get("cursos") or []:
                for pers in curso.get("personas") or []:
                    ws.cell(row=row_idx, column=1, value=sec.get("programa_nombre"))
                    ws.cell(row=row_idx, column=2, value=sec.get("plan_nombre"))
                    ws.cell(row=row_idx, column=3, value=curso.get("curso_nombre"))
                    ws.cell(row=row_idx, column=4, value=pers.get("persona"))
                    ws.cell(row=row_idx, column=5, value=pers.get("puesto"))
                    ws.cell(row=row_idx, column=6, value=pers.get("estado"))
                    ws.cell(row=row_idx, column=7, value=pers.get("nota"))
                    ws.cell(row=row_idx, column=8, value=pers.get("horas_acreditadas"))
                    ws.cell(row=row_idx, column=9, value=pers.get("fecha_vencimiento"))
                    row_idx += 1

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
