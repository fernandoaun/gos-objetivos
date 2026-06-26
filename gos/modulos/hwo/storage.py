"""Persistencia HWO en la base principal de GOS (PostgreSQL / SQLite)."""
from __future__ import annotations

import json
import shutil
import sqlite3
import time
from pathlib import Path

from gos.extensions import db
from gos.modulos.hwo.database import DATA_DIR, DB_PATH, LEGACY_DATA_DIR
from gos.modulos.hwo.models import HwoDataset, HwoModalidad

DATASETS_FILE = DATA_DIR / "datasets.json"
MODALIDAD_FILE = DATA_DIR / "modalidad.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def migrate_legacy_data_if_empty() -> None:
    """Migra JSON o SQLite local si la tabla principal está vacía."""
    _ensure_data_dir()
    if HwoDataset.query.limit(1).first() is not None:
        return
    _copy_legacy_json_if_missing()
    if _migrate_json_to_db():
        return
    _migrate_local_sqlite_to_db()


def _copy_legacy_json_if_missing() -> None:
    if not LEGACY_DATA_DIR.is_dir():
        return
    for name in ("datasets.json", "modalidad.json"):
        src = LEGACY_DATA_DIR / name
        dst = DATA_DIR / name
        if src.is_file() and (
            not dst.is_file() or not dst.read_text(encoding="utf-8").strip().strip("{}").strip()
        ):
            shutil.copy2(src, dst)


def _insert_dataset(name: str, saved_at: int, config_raw: dict, rows_raw: list) -> None:
    db.session.add(
        HwoDataset(
            name=name,
            saved_at=saved_at,
            config_raw=json.dumps(config_raw, ensure_ascii=False),
            rows_raw=json.dumps(rows_raw, ensure_ascii=False),
        )
    )


def _insert_modalidad(prefs: dict) -> None:
    for equipo, schedule in prefs.items():
        if not equipo or not schedule:
            continue
        db.session.add(HwoModalidad(equipo=str(equipo), schedule=str(schedule)))


def _migrate_json_to_db() -> bool:
    datasets = _read_json(DATASETS_FILE)
    modalidad = _read_json(MODALIDAD_FILE)
    if not datasets and not modalidad:
        return False
    try:
        for name, row in datasets.items():
            if not isinstance(row, dict):
                continue
            config_raw = row.get("configRaw")
            rows_raw = row.get("rowsRaw")
            if config_raw is None or rows_raw is None:
                continue
            _insert_dataset(
                name,
                int(row.get("savedAt") or time.time() * 1000),
                config_raw,
                rows_raw,
            )
        _insert_modalidad(modalidad)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        raise


def _migrate_local_sqlite_to_db() -> bool:
    if not DB_PATH.is_file():
        return False
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            ds_rows = conn.execute(
                "SELECT name, saved_at, config_raw, rows_raw FROM hwo_datasets"
            ).fetchall()
            if not ds_rows:
                return False
            for row in ds_rows:
                _insert_dataset(
                    row["name"],
                    int(row["saved_at"]),
                    json.loads(row["config_raw"]),
                    json.loads(row["rows_raw"]),
                )
            mod_rows = conn.execute(
                "SELECT equipo, schedule FROM hwo_modalidad"
            ).fetchall()
            for row in mod_rows:
                db.session.add(
                    HwoModalidad(equipo=row["equipo"], schedule=row["schedule"])
                )
            db.session.commit()
            return True
        finally:
            conn.close()
    except Exception:
        db.session.rollback()
        raise


def get_all_datasets() -> list[dict]:
    rows = HwoDataset.query.order_by(HwoDataset.saved_at.desc()).all()
    items = []
    for row in rows:
        rows_raw = json.loads(row.rows_raw)
        items.append(
            {
                "name": row.name,
                "saved_at": row.saved_at,
                "row_count": len(rows_raw) if isinstance(rows_raw, list) else 0,
            }
        )
    return items


def get_dataset(name: str) -> dict | None:
    row = HwoDataset.query.filter_by(name=name).first()
    if not row:
        return None
    return {
        "name": row.name,
        "savedAt": row.saved_at,
        "configRaw": json.loads(row.config_raw),
        "rowsRaw": json.loads(row.rows_raw),
    }


def save_dataset(name: str, config_raw: dict, rows_raw: list) -> None:
    saved_at = int(time.time() * 1000)
    config_text = json.dumps(config_raw, ensure_ascii=False)
    rows_text = json.dumps(rows_raw, ensure_ascii=False)
    row = HwoDataset.query.filter_by(name=name).first()
    if row:
        row.saved_at = saved_at
        row.config_raw = config_text
        row.rows_raw = rows_text
    else:
        db.session.add(
            HwoDataset(
                name=name,
                saved_at=saved_at,
                config_raw=config_text,
                rows_raw=rows_text,
            )
        )
    db.session.commit()


def delete_dataset(name: str) -> None:
    HwoDataset.query.filter_by(name=name).delete()
    db.session.commit()


def clear_datasets() -> None:
    HwoDataset.query.delete()
    db.session.commit()


def get_all_modalidad() -> dict:
    return {row.equipo: row.schedule for row in HwoModalidad.query.all()}


def save_modalidad(prefs: dict) -> None:
    for equipo, schedule in prefs.items():
        if not equipo or not schedule:
            continue
        row = HwoModalidad.query.filter_by(equipo=str(equipo)).first()
        if row:
            row.schedule = str(schedule)
        else:
            db.session.add(HwoModalidad(equipo=str(equipo), schedule=str(schedule)))
    db.session.commit()


def reset_for_tests() -> None:
    """Limpia tablas HWO (solo tests)."""
    HwoModalidad.query.delete()
    HwoDataset.query.delete()
    db.session.commit()
