"""Snapshots de Capacitación para poder recuperar vínculos si algo falla."""

from __future__ import annotations

import gzip
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect, text

from gos.extensions import db

logger = logging.getLogger(__name__)

KEEP_SNAPSHOTS = 30
_SNAP_NAME_RE = re.compile(r"^\d{8}-\d{6}-.+\.json\.gz$")


def _snapshots_dir() -> Path:
    try:
        from flask import current_app

        root = Path(current_app.root_path).parent
    except Exception:
        root = Path(__file__).resolve().parents[4]
    path = root / "storage" / "capacitacion" / "snapshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def listar_tablas_cap() -> list[str]:
    """Tablas cap_* presentes en la base activa (orden estable)."""
    existing = set(inspect(db.engine).get_table_names())
    return sorted(name for name in existing if name.startswith("cap_"))


def snapshot_capacitacion(*, motivo: str = "manual") -> Path | None:
    """Exporta todas las tablas cap_* a un JSON.gz. No modifica datos."""
    motivo_safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", (motivo or "manual").strip())[:40] or "manual"
    tables = listar_tablas_cap()
    if not tables:
        return None

    payload: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "motivo": motivo,
        "tables": {},
        "counts": {},
    }
    with db.engine.connect() as conn:
        for table in tables:
            rows = conn.execute(text(f'SELECT * FROM "{table}"')).mappings().all()
            data = [dict(row) for row in rows]
            payload["tables"][table] = data
            payload["counts"][table] = len(data)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = _snapshots_dir() / f"{stamp}-{motivo_safe}.json.gz"
    raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    dest.write_bytes(gzip.compress(raw, compresslevel=6))
    _prune_snapshots()
    logger.info(
        "Snapshot capacitación %s (%s tablas, %s filas)",
        dest.name,
        len(tables),
        sum(payload["counts"].values()),
    )
    return dest


def maybe_daily_snapshot(*, motivo: str = "daily") -> Path | None:
    """Como máximo un snapshot automático por día UTC."""
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    for path in _snapshots_dir().glob("*.json.gz"):
        if path.name.startswith(day):
            return None
    try:
        return snapshot_capacitacion(motivo=motivo)
    except Exception:
        logger.exception("No se pudo crear snapshot diario de capacitación")
        return None


def _prune_snapshots() -> None:
    files = sorted(
        (p for p in _snapshots_dir().glob("*.json.gz") if _SNAP_NAME_RE.match(p.name)),
        key=lambda p: p.name,
        reverse=True,
    )
    for old in files[KEEP_SNAPSHOTS:]:
        try:
            old.unlink()
        except OSError:
            pass
