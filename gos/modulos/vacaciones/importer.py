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
from sqlalchemy import select
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
_SET_VACACION = (
    "empleado", "fecha_ingreso", "sector",
    "dias_disponibles", "dias_tomados", "dias_pendientes",
)


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


# ── Hoja PLANILLA VACACIONES (pequeña: una fila por empleado) ───────────────


def _parse_year_block(data_rows: list[tuple], col_offset: int, anio: int) -> list[dict]:
    rows = []
    for row in data_rows:
        empleado = _to_str(_cell(row, 1))
        if not empleado:
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
    wb = _open_workbook(filepath)
    try:
        if "PLANILLA VACACIONES" not in wb.sheetnames:
            return
        all_rows = list(wb["PLANILLA VACACIONES"].iter_rows(values_only=True))
    finally:
        wb.close()

    data_rows = all_rows[4:]
    all_vac = (
        _parse_year_block(data_rows, 5, 2023)
        + _parse_year_block(data_rows, 9, 2024)
        + _parse_year_block(data_rows, 13, 2025)
    )
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

    for rec in all_vac:
        stmt = _insert(Vacacion, db).values(rec)
        stmt = stmt.on_conflict_do_update(
            index_elements=["legajo", "anio"],
            set_={c: getattr(stmt.excluded, c) for c in _SET_VACACION},
        )
        db.execute(stmt)
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
