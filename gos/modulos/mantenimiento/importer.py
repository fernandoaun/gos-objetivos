"""Importación del plan de mantenimiento desde Excel (formato VTV / Informe Pampa).

Hojas esperadas:
- Informe: plan anual por unidad con columnas mensuales R / P / E
- VTV: unidad + vencimiento VTV
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from gos.modulos.mantenimiento.models import MantPlanCelda, MantPlanMeta, MantUnidad, MantVtv

MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def normalizar_codigo(raw: str) -> str:
    """HG 01 / HG-01 / hg01 → HG01. También unifica UI↔UL (typo frecuente en el Excel)."""
    s = re.sub(r"[^A-Za-z0-9]", "", (raw or "").strip().upper())
    if s.startswith("UI") and len(s) > 2 and s[2:].isdigit():
        s = "UL" + s[2:]
    return s


def _cell_num(value) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return 0.0


def _parse_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _find_sheet(wb, *candidates: str):
    lower = {name.lower().strip(): name for name in wb.sheetnames}
    for cand in candidates:
        if cand.lower() in lower:
            return wb[lower[cand.lower()]]
    for name in wb.sheetnames:
        nl = name.lower()
        if any(c.lower() in nl for c in candidates):
            return wb[name]
    return None


def _get_or_create_unidad(session: Session, nombre: str, cache: dict[str, MantUnidad]) -> MantUnidad:
    codigo = normalizar_codigo(nombre)
    if not codigo:
        raise ValueError(f"Código de unidad inválido: {nombre!r}")
    if codigo in cache:
        unidad = cache[codigo]
        if nombre.strip() and unidad.nombre != nombre.strip():
            # Preferir el nombre con espacios del plan (HG 01) sobre HG-01
            if " " in nombre.strip() or len(nombre.strip()) > len(unidad.nombre):
                unidad.nombre = nombre.strip()
        return unidad

    unidad = session.execute(
        select(MantUnidad).where(MantUnidad.codigo == codigo)
    ).scalar_one_or_none()
    if unidad is None:
        unidad = MantUnidad(codigo=codigo, nombre=nombre.strip() or codigo, activo=True)
        session.add(unidad)
        session.flush()
    else:
        unidad.nombre = nombre.strip() or unidad.nombre
        unidad.activo = True
    cache[codigo] = unidad
    return unidad


def _parse_informe(ws, session: Session, cache: dict[str, MantUnidad]) -> dict:
    titulo = None
    anio = None
    sector = None
    observaciones = None

    for r in range(1, min(9, (ws.max_row or 1) + 1)):
        for c in range(1, min(50, (ws.max_column or 1) + 1)):
            val = ws.cell(r, c).value
            if val is None:
                continue
            text = str(val).strip()
            if not text:
                continue
            low = text.lower()
            if titulo is None and "plan de mantenimiento" in low:
                titulo = text
            if low.startswith("fecha:") or (c <= 4 and re.search(r"20\d{2}", text) and "fecha" in low):
                m = re.search(r"(20\d{2})", text)
                if m:
                    anio = int(m.group(1))
            if low == "sector:" or low.startswith("sector"):
                # valor suele estar a la derecha en celdas mergeadas
                for cc in range(c + 1, min(c + 15, (ws.max_column or c) + 1)):
                    vv = ws.cell(r, cc).value
                    if vv and str(vv).strip() and str(vv).strip().lower() not in ("sector:", "sector"):
                        sector = str(vv).strip()
                        break
            if "observacion" in low:
                observaciones = text

    # Año también puede venir solo como número cerca de FECHA
    if anio is None:
        for r in range(1, 9):
            for c in range(1, 10):
                val = ws.cell(r, c).value
                if isinstance(val, int) and 2000 <= val <= 2100:
                    anio = val
                elif isinstance(val, str):
                    m = re.search(r"(20\d{2})", val)
                    if m:
                        anio = int(m.group(1))

    header_row = None
    rpe_row = None
    mes_cols: dict[int, dict[str, int]] = {}  # mes -> {R,P,E: col}

    for r in range(1, min(20, (ws.max_row or 1) + 1)):
        month_hits = []
        for c in range(1, (ws.max_column or 1) + 1):
            val = ws.cell(r, c).value
            if not isinstance(val, str):
                continue
            key = val.strip().lower()
            if key in MESES:
                month_hits.append((c, MESES[key]))
        if len(month_hits) >= 3:
            header_row = r
            rpe_row = r + 1
            for col, mes in month_hits:
                # R P E suelen ocupar col, col+1, col+2
                labels = {}
                for offset, expected in enumerate(("R", "P", "E")):
                    cell_val = ws.cell(rpe_row, col + offset).value
                    label = str(cell_val).strip().upper() if cell_val is not None else expected
                    if label in ("R", "P", "E"):
                        labels[label.lower()] = col + offset
                    else:
                        labels[expected.lower()] = col + offset
                mes_cols[mes] = labels
            break

    if header_row is None or anio is None:
        raise ValueError(
            "No se pudo leer el plan en la hoja Informe "
            "(faltan fila de meses o año FECHA)."
        )

    # Ubicar columna UNIDADES
    unidad_col = 2
    for c in range(1, 8):
        val = ws.cell(header_row, c).value
        if isinstance(val, str) and "unidad" in val.lower():
            unidad_col = c
            break

    celdas = 0
    unidades_plan = 0
    start = rpe_row + 1
    for r in range(start, (ws.max_row or start) + 1):
        raw_nombre = ws.cell(r, unidad_col).value
        if raw_nombre is None or not str(raw_nombre).strip():
            # fila de totales suele tener fórmulas en P/E sin nombre
            continue
        nombre = str(raw_nombre).strip()
        if nombre.lower() in ("total", "totales", "suma"):
            continue
        # ignorar filas sin ningún dato R/P/E
        tiene = False
        for labels in mes_cols.values():
            for col in labels.values():
                if ws.cell(r, col).value not in (None, ""):
                    tiene = True
                    break
            if tiene:
                break
        if not tiene:
            continue

        unidad = _get_or_create_unidad(session, nombre, cache)
        unidades_plan += 1

        # Reemplazar celdas del año para esta unidad
        session.execute(
            delete(MantPlanCelda).where(
                MantPlanCelda.unidad_id == unidad.id,
                MantPlanCelda.anio == anio,
            )
        )

        for mes, labels in mes_cols.items():
            rv = _cell_num(ws.cell(r, labels.get("r", 0)).value) if labels.get("r") else 0.0
            pv = _cell_num(ws.cell(r, labels.get("p", 0)).value) if labels.get("p") else 0.0
            ev = _cell_num(ws.cell(r, labels.get("e", 0)).value) if labels.get("e") else 0.0
            if rv == 0 and pv == 0 and ev == 0:
                continue
            session.add(
                MantPlanCelda(
                    unidad_id=unidad.id,
                    anio=anio,
                    mes=mes,
                    r=rv,
                    p=pv,
                    e=ev,
                )
            )
            celdas += 1

    meta = session.execute(
        select(MantPlanMeta).where(MantPlanMeta.anio == anio)
    ).scalar_one_or_none()
    if meta is None:
        meta = MantPlanMeta(anio=anio)
        session.add(meta)
    meta.titulo = titulo or meta.titulo
    meta.sector = sector or meta.sector
    meta.observaciones = observaciones or meta.observaciones

    return {
        "anio": anio,
        "titulo": titulo,
        "sector": sector,
        "unidades_plan": unidades_plan,
        "celdas": celdas,
    }


def _parse_vtv(ws, session: Session, cache: dict[str, MantUnidad]) -> dict:
    header_row = None
    col_unidad = None
    col_vto = None

    for r in range(1, min(30, (ws.max_row or 1) + 1)):
        for c in range(1, min(20, (ws.max_column or 1) + 1)):
            val = ws.cell(r, c).value
            if not isinstance(val, str):
                continue
            low = val.strip().lower()
            if low in ("unidad", "unidades", "equipo", "vehiculo", "vehículo"):
                header_row = r
                col_unidad = c
            if header_row == r and ("venc" in low or "vtv" in low):
                col_vto = c
        if header_row and col_unidad and col_vto:
            break

    if not header_row or not col_unidad or not col_vto:
        # fallback formato conocido: C=Unidad, D=Vencimiento
        header_row = 5
        col_unidad = 3
        col_vto = 4

    cargados = 0
    for r in range(header_row + 1, (ws.max_row or header_row) + 1):
        raw = ws.cell(r, col_unidad).value
        if raw is None or not str(raw).strip():
            continue
        nombre = str(raw).strip()
        venc = _parse_date(ws.cell(r, col_vto).value)
        if not venc:
            continue
        unidad = _get_or_create_unidad(session, nombre, cache)
        existing = session.execute(
            select(MantVtv).where(MantVtv.unidad_id == unidad.id)
        ).scalar_one_or_none()
        if existing is None:
            session.add(MantVtv(unidad_id=unidad.id, vencimiento=venc))
        else:
            existing.vencimiento = venc
        cargados += 1

    return {"vtv": cargados}


def import_vtv_excel(path: str | Path, session: Session) -> dict:
    path = Path(path)
    wb = load_workbook(path, data_only=True)
    cache: dict[str, MantUnidad] = {}

    informe = _find_sheet(wb, "Informe", "Plan", "Mantenimiento")
    vtv_sheet = _find_sheet(wb, "VTV", "Vtv")

    result = {
        "anio": None,
        "titulo": None,
        "sector": None,
        "unidades_plan": 0,
        "celdas": 0,
        "vtv": 0,
        "hojas": wb.sheetnames,
    }

    if informe is None and vtv_sheet is None:
        raise ValueError(
            "El Excel no tiene hojas 'Informe' ni 'VTV'. "
            f"Hojas encontradas: {', '.join(wb.sheetnames)}"
        )

    if informe is not None:
        info = _parse_informe(informe, session, cache)
        result.update(info)

    if vtv_sheet is not None:
        vtv_info = _parse_vtv(vtv_sheet, session, cache)
        result.update(vtv_info)

    session.commit()
    return result
