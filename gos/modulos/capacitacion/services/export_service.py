"""Exportación de datos de capacitaciones a Excel."""

from io import BytesIO

import openpyxl
from openpyxl.styles import Font, PatternFill

from gos.modulos.capacitacion.services.matriz_service import matriz_capacitaciones


def exportar_matriz_excel(empresa_id: int, **filtros) -> BytesIO:
    data = matriz_capacitaciones(empresa_id, **filtros)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Matriz capacitaciones"

    header_fill = PatternFill(start_color="1B4332", end_color="1B4332", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    headers = ["Persona", "Legajo", "Sector"] + [c["codigo"] for c in data["columnas"]]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font

    color_map = {
        "verde": "C6EFCE",
        "amarillo": "FFEB9C",
        "rojo": "FFC7CE",
        "azul": "BDD7EE",
        "gris": "D9D9D9",
    }

    for row_idx, fila in enumerate(data["filas"], 2):
        ws.cell(row=row_idx, column=1, value=fila["nombre"])
        ws.cell(row=row_idx, column=2, value=fila.get("legajo") or "")
        ws.cell(row=row_idx, column=3, value=fila.get("sector_nombre") or "")
        for col_idx, col in enumerate(data["columnas"], 4):
            celda = fila["celdas"].get(str(col["id"]), {})
            estado = celda.get("estado", "no_aplica")
            cell = ws.cell(row=row_idx, column=col_idx, value=estado)
            fill_color = color_map.get(celda.get("color", "gris"), "D9D9D9")
            cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
