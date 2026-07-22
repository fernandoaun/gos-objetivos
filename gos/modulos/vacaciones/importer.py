"""Importación de vacaciones desde Excel.

La lectura se hace por *streaming* (openpyxl en modo read-only) para que el
uso de memoria sea plano sin importar el tamaño del archivo: las filas se
procesan y se guardan de a lotes, sin materializar nunca la hoja completa.
Esto evita que un archivo grande agote la memoria del servidor (OOM).
"""

from __future__ import annotations

import math
from datetime import date, datetime

import openpyxl
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from gos.modulos.vacaciones.models import Registro, Vacacion

COLS_TOTAL = [
    "fecha", "empleado", "sector", "servicio", "centro", "situacion",
    "total_horas", "hs_viaje", "hs50", "hs_noc", "hs_noc50", "hs100",
    "viandas", "v_desayuno", "d_normales", "ausente", "fr_trabajados",
    "feriados", "enfermedad", "traslado", "vacaciones", "licencia",
    "suspension", "accidente", "francos_comp",
]

# Columnas de texto y numéricas de la hoja TOTAL (según el modelo Registro).
_TEXT_COLS = frozenset(COLS_TOTAL[2:6])          # sector, servicio, centro, situacion
_FLOAT_COLS = frozenset(COLS_TOTAL[6:12])         # total_horas … hs100
_INT_COLS = frozenset(COLS_TOTAL[12:])            # viandas … francos_comp

CHUNK_SIZE = 500

_SET_REGISTRO = {c: c for c in COLS_TOTAL[2:]}    # columnas actualizables en el upsert


# ── Coerción de valores ────────────────────────────────────────────────────


def _to_float(value) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return 0.0 if (isinstance(value, float) and math.isnan(value)) else float(value)
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return 0.0


def _to_int(value) -> int:
    try:
        return int(_to_float(value))
    except (ValueError, OverflowError):
        return 0


def _to_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _cell(row: tuple, idx: int):
    return row[idx] if idx < len(row) else None


# ── Upsert (Postgres / SQLite) ─────────────────────────────────────────────


def _insert(model, session: Session):
    if session.get_bind().dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert(model)


def _open_workbook(filepath: str):
    """Abre el .xlsx/.xlsm en modo read-only (lectura por streaming)."""
    try:
        return openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    except Exception as exc:  # archivo corrupto, .xls disfrazado, etc.
        raise ValueError(
            "No se pudo leer el archivo. Asegurate de que sea un Excel válido "
            "(.xlsx o .xlsm)."
        ) from exc


# ── Hoja TOTAL (streaming) ─────────────────────────────────────────────────


def _iter_total_keys(filepath: str):
    """Primera pasada liviana: solo (fecha, empleado) para contar y acotar rango."""
    wb = _open_workbook(filepath)
    try:
        if "TOTAL" not in wb.sheetnames:
            return
        rows = wb["TOTAL"].iter_rows(min_col=1, max_col=2, values_only=True)
        next(rows, None)  # descartar encabezado
        for row in rows:
            fecha = _to_date(_cell(row, 0))
            empleado = _to_str(_cell(row, 1))
            if fecha is None or not empleado:
                continue
            yield fecha, empleado
    finally:
        wb.close()


def _iter_total_records(filepath: str):
    """Segunda pasada: filas limpias listas para el upsert."""
    wb = _open_workbook(filepath)
    try:
        if "TOTAL" not in wb.sheetnames:
            return
        rows = wb["TOTAL"].iter_rows(values_only=True)
        header = next(rows, None)
        if header is None:
            return
        ncols = min(len(header), len(COLS_TOTAL))
        cols = COLS_TOTAL[:ncols]
        for row in rows:
            fecha = _to_date(_cell(row, 0))
            if fecha is None:
                continue
            empleado = _to_str(_cell(row, 1))
            if not empleado:
                continue
            rec = {"fecha": fecha, "empleado": empleado}
            for idx in range(2, ncols):
                name = cols[idx]
                val = _cell(row, idx)
                if name in _INT_COLS:
                    rec[name] = _to_int(val)
                elif name in _FLOAT_COLS:
                    rec[name] = _to_float(val)
                else:
                    rec[name] = _to_str(val)
            yield rec
    finally:
        wb.close()


def _flush_registros(chunk: list[dict], db: Session) -> None:
    stmt = _insert(Registro, db).values(chunk)
    stmt = stmt.on_conflict_do_update(
        index_elements=["fecha", "empleado"],
        set_={c: getattr(stmt.excluded, c) for c in _SET_REGISTRO},
    )
    db.execute(stmt)


def _import_total(filepath: str, db: Session, result: dict) -> None:
    # Pasada 1: contar nuevos vs. actualizados sin cargar los datos completos.
    keys_en_excel: set[tuple] = set()
    min_date: date | None = None
    max_date: date | None = None
    for fecha, empleado in _iter_total_keys(filepath):
        keys_en_excel.add((fecha, empleado))
        if min_date is None or fecha < min_date:
            min_date = fecha
        if max_date is None or fecha > max_date:
            max_date = fecha

    if keys_en_excel:
        existing = db.execute(
            select(Registro.fecha, Registro.empleado).where(
                Registro.fecha >= min_date,
                Registro.fecha <= max_date,
            )
        ).fetchall()
        existing_keys = {(row.fecha, row.empleado) for row in existing}
        result["registros_nuevos"] = len(keys_en_excel - existing_keys)
        result["registros_actualizados"] = len(keys_en_excel & existing_keys)

    # Pasada 2: guardar por lotes (commit por lote para no acumular memoria).
    total = 0
    chunk: list[dict] = []
    for rec in _iter_total_records(filepath):
        chunk.append(rec)
        if len(chunk) >= CHUNK_SIZE:
            _flush_registros(chunk, db)
            db.commit()
            total += len(chunk)
            chunk = []
    if chunk:
        _flush_registros(chunk, db)
        db.commit()
        total += len(chunk)
    result["registros"] = total


# ── Planilla de vacaciones (una fila por empleado, bloques por año) ─────────


def _norm_header(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip().lower()
    for old, new in (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n"),
    ):
        text = text.replace(old, new)
    return " ".join(text.split())


def _find_year_in_header(value) -> int | None:
    text = _norm_header(value)
    if "vacacion" not in text:
        return None
    for token in text.replace("-", " ").split():
        if token.isdigit() and len(token) == 4:
            year = int(token)
            if 2000 <= year <= 2100:
                return year
    return None


def _detect_planilla_sheet(wb) -> str | None:
    """Elige la hoja de planilla: nombre conocido o detección por encabezados."""
    preferred = ("PLANILLA VACACIONES", "PLANILLA", "VACACIONES")
    for name in preferred:
        if name in wb.sheetnames:
            return name

    best_name = None
    best_score = 0
    for name in wb.sheetnames:
        rows = list(wb[name].iter_rows(max_row=5, values_only=True))
        flat = [_norm_header(c) for row in rows for c in (row or ())]
        joined = " ".join(flat)
        score = 0
        if any("legajo" in h for h in flat):
            score += 2
        if any(h == "empleado" or h.endswith(" empleado") for h in flat):
            score += 2
        if "vacacion" in joined:
            score += 2
        if any(_find_year_in_header(c) for row in rows for c in (row or ())):
            score += 2
        if score > best_score:
            best_score = score
            best_name = name
    return best_name if best_score >= 4 else None


def _detect_year_blocks(header_rows: list[tuple]) -> list[tuple[int, int]]:
    """Devuelve [(anio, col_offset_dias_disponibles), ...] desde los encabezados."""
    blocks: list[tuple[int, int]] = []
    seen: set[int] = set()
    for row in header_rows:
        for idx, cell in enumerate(row or ()):
            anio = _find_year_in_header(cell)
            if anio is None or anio in seen:
                continue
            # El título del bloque suele estar sobre "Días disponibles".
            blocks.append((anio, idx))
            seen.add(anio)
    if blocks:
        return sorted(blocks, key=lambda x: x[0])
    # Fallback del layout histórico: disponibles en cols 5 / 9 / 13.
    return [(2023, 5), (2024, 9), (2025, 13)]


def _find_data_start(all_rows: list[tuple]) -> int:
    """Primera fila con legajo numérico + nombre de empleado."""
    for i, row in enumerate(all_rows):
        legajo = _cell(row, 0)
        empleado = _to_str(_cell(row, 1))
        if not empleado:
            continue
        if isinstance(legajo, (int, float)) and not isinstance(legajo, bool):
            return i
        if isinstance(legajo, str) and legajo.strip().isdigit():
            return i
    return min(4, len(all_rows))


def _year_block_has_data(row: tuple, col_offset: int) -> bool:
    return any(_cell(row, col_offset + i) not in (None, "") for i in range(3))


def _parse_year_block(
    data_rows: list[tuple], col_offset: int, anio: int
) -> list[dict]:
    rows = []
    for row in data_rows:
        empleado = _to_str(_cell(row, 1))
        if not empleado:
            continue
        if not _year_block_has_data(row, col_offset):
            continue
        legajo_raw = _cell(row, 0)
        rows.append(
            {
                "legajo": _to_int(legajo_raw) if legajo_raw not in (None, "") else None,
                "empleado": empleado,
                "fecha_ingreso": _to_date(_cell(row, 2)),
                "sector": _to_str(_cell(row, 3)),
                "anio": anio,
                "dias_disponibles": _to_int(_cell(row, col_offset)),
                "dias_tomados": _to_int(_cell(row, col_offset + 1)),
                "dias_pendientes": _to_int(_cell(row, col_offset + 2)),
            }
        )
    return rows


def _import_planilla(filepath: str, db: Session, result: dict) -> None:
    # La planilla es chica (una fila por empleado); se abre sin read-only
    # porque la detección de hoja + lectura de filas requiere varias pasadas.
    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
    except Exception as exc:
        raise ValueError(
            "No se pudo leer el archivo. Asegurate de que sea un Excel válido "
            "(.xlsx o .xlsm)."
        ) from exc
    try:
        sheet_name = _detect_planilla_sheet(wb)
        if not sheet_name:
            return
        all_rows = list(wb[sheet_name].iter_rows(values_only=True))
    finally:
        wb.close()

    if not all_rows:
        return

    data_start = _find_data_start(all_rows)
    header_rows = all_rows[:data_start]
    data_rows = all_rows[data_start:]
    year_blocks = _detect_year_blocks(header_rows)

    all_vac: list[dict] = []
    for anio, col_offset in year_blocks:
        all_vac.extend(_parse_year_block(data_rows, col_offset, anio))
    if not all_vac:
        return

    anios_en_excel = {r["anio"] for r in all_vac}
    existing_vac = db.execute(
        select(Vacacion.legajo, Vacacion.anio).where(Vacacion.anio.in_(anios_en_excel))
    ).fetchall()
    existing_vac_keys = {(row.legajo, row.anio) for row in existing_vac}
    keys_vac_excel = {(r["legajo"], r["anio"]) for r in all_vac}
    result["vacaciones_nuevas"] = len(keys_vac_excel - existing_vac_keys)
    result["vacaciones_actualizadas"] = len(keys_vac_excel & existing_vac_keys)

    # Reemplazo por año: el Excel actualizado es la fuente de verdad de esos períodos.
    db.execute(delete(Vacacion).where(Vacacion.anio.in_(anios_en_excel)))
    db.bulk_insert_mappings(Vacacion, all_vac)
    db.commit()
    result["vacaciones"] = len(all_vac)


# ── Punto de entrada ────────────────────────────────────────────────────────


def import_excel(filepath: str, db: Session) -> dict:
    result = {
        "registros": 0,
        "registros_nuevos": 0,
        "registros_actualizados": 0,
        "vacaciones": 0,
        "vacaciones_nuevas": 0,
        "vacaciones_actualizadas": 0,
        "errores": [],
    }

    _import_total(filepath, db, result)
    _import_planilla(filepath, db, result)

    return result
