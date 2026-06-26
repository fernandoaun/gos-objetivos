"""Persistencia SQLite del módulo HWO (datasets y modalidad)."""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from gos import env
from gos.config import BASE_DIR
from gos.modulos.hwo.database import DATA_DIR, get_session, init_db
from gos.modulos.hwo.models import HwoDataset, HwoModalidad

DATASETS_FILE = DATA_DIR / "datasets.json"
MODALIDAD_FILE = DATA_DIR / "modalidad.json"
LEGACY_DATA_DIR = BASE_DIR.parent / "Analisis HWO" / "data"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def migrate_legacy_data_if_empty() -> None:
    """Inicializa SQLite y migra JSON legacy si la base está vacía."""
    _ensure_data_dir()
    init_db()
    _copy_legacy_json_if_missing()
    _migrate_json_to_db_if_empty()


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


def _migrate_json_to_db_if_empty() -> None:
    session = get_session()
    try:
        if session.query(HwoDataset).limit(1).first() is not None:
            return

        datasets = _read_json(DATASETS_FILE)
        for name, row in datasets.items():
            if not isinstance(row, dict):
                continue
            config_raw = row.get("configRaw")
            rows_raw = row.get("rowsRaw")
            if config_raw is None or rows_raw is None:
                continue
            session.add(
                HwoDataset(
                    name=name,
                    saved_at=int(row.get("savedAt") or time.time() * 1000),
                    config_raw=json.dumps(config_raw, ensure_ascii=False),
                    rows_raw=json.dumps(rows_raw, ensure_ascii=False),
                )
            )

        modalidad = _read_json(MODALIDAD_FILE)
        for equipo, schedule in modalidad.items():
            if not equipo or not schedule:
                continue
            session.add(HwoModalidad(equipo=str(equipo), schedule=str(schedule)))

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_all_datasets() -> list[dict]:
    session = get_session()
    try:
        rows = session.query(HwoDataset).order_by(HwoDataset.saved_at.desc()).all()
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
    finally:
        session.close()


def get_dataset(name: str) -> dict | None:
    session = get_session()
    try:
        row = session.query(HwoDataset).filter_by(name=name).first()
        if not row:
            return None
        return {
            "name": row.name,
            "savedAt": row.saved_at,
            "configRaw": json.loads(row.config_raw),
            "rowsRaw": json.loads(row.rows_raw),
        }
    finally:
        session.close()


def save_dataset(name: str, config_raw: dict, rows_raw: list) -> None:
    session = get_session()
    try:
        saved_at = int(time.time() * 1000)
        config_text = json.dumps(config_raw, ensure_ascii=False)
        rows_text = json.dumps(rows_raw, ensure_ascii=False)
        row = session.query(HwoDataset).filter_by(name=name).first()
        if row:
            row.saved_at = saved_at
            row.config_raw = config_text
            row.rows_raw = rows_text
        else:
            session.add(
                HwoDataset(
                    name=name,
                    saved_at=saved_at,
                    config_raw=config_text,
                    rows_raw=rows_text,
                )
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_dataset(name: str) -> None:
    session = get_session()
    try:
        session.query(HwoDataset).filter_by(name=name).delete()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def clear_datasets() -> None:
    session = get_session()
    try:
        session.query(HwoDataset).delete()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_all_modalidad() -> dict:
    session = get_session()
    try:
        rows = session.query(HwoModalidad).all()
        return {row.equipo: row.schedule for row in rows}
    finally:
        session.close()


def save_modalidad(prefs: dict) -> None:
    session = get_session()
    try:
        for equipo, schedule in prefs.items():
            if not equipo or not schedule:
                continue
            row = session.query(HwoModalidad).filter_by(equipo=str(equipo)).first()
            if row:
                row.schedule = str(schedule)
            else:
                session.add(HwoModalidad(equipo=str(equipo), schedule=str(schedule)))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
