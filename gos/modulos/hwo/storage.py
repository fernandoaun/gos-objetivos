"""Persistencia JSON del módulo HWO (equivalente a db.js)."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from gos.config import BASE_DIR

DATA_DIR = BASE_DIR / "instance" / "hwo"
DATASETS_FILE = DATA_DIR / "datasets.json"
MODALIDAD_FILE = DATA_DIR / "modalidad.json"
LEGACY_DATA_DIR = BASE_DIR.parent / "Analisis HWO" / "data"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATASETS_FILE.is_file():
        DATASETS_FILE.write_text("{}", encoding="utf-8")
    if not MODALIDAD_FILE.is_file():
        MODALIDAD_FILE.write_text("{}", encoding="utf-8")


def migrate_legacy_data_if_empty() -> None:
    """Copia datos del proyecto HWO standalone si el módulo está vacío."""
    _ensure_data_dir()
    datasets = _read_json(DATASETS_FILE)
    if datasets:
        return
    if not LEGACY_DATA_DIR.is_dir():
        return
    for name in ("datasets.json", "modalidad.json"):
        src = LEGACY_DATA_DIR / name
        dst = DATA_DIR / name
        if src.is_file() and not dst.read_text(encoding="utf-8").strip().strip("{}").strip():
            shutil.copy2(src, dst)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_all_datasets() -> list[dict]:
    _ensure_data_dir()
    all_data = _read_json(DATASETS_FILE)
    items = []
    for row in all_data.values():
        rows_raw = row.get("rowsRaw") or []
        items.append(
            {
                "name": row.get("name", ""),
                "saved_at": row.get("savedAt", 0),
                "row_count": len(rows_raw) if isinstance(rows_raw, list) else 0,
            }
        )
    items.sort(key=lambda x: x["saved_at"], reverse=True)
    return items


def get_dataset(name: str) -> dict | None:
    _ensure_data_dir()
    return _read_json(DATASETS_FILE).get(name)


def save_dataset(name: str, config_raw: dict, rows_raw: list) -> None:
    _ensure_data_dir()
    all_data = _read_json(DATASETS_FILE)
    all_data[name] = {
        "name": name,
        "savedAt": int(time.time() * 1000),
        "configRaw": config_raw,
        "rowsRaw": rows_raw,
    }
    _write_json(DATASETS_FILE, all_data)


def delete_dataset(name: str) -> None:
    _ensure_data_dir()
    all_data = _read_json(DATASETS_FILE)
    all_data.pop(name, None)
    _write_json(DATASETS_FILE, all_data)


def clear_datasets() -> None:
    _ensure_data_dir()
    _write_json(DATASETS_FILE, {})


def get_all_modalidad() -> dict:
    _ensure_data_dir()
    return _read_json(MODALIDAD_FILE)


def save_modalidad(prefs: dict) -> None:
    _ensure_data_dir()
    current = _read_json(MODALIDAD_FILE)
    current.update(prefs)
    _write_json(MODALIDAD_FILE, current)
