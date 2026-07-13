"""Persistencia Ralentí en la base principal de GOS (PostgreSQL / SQLite)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from gos.extensions import db
from gos.modulos.ralenti.database import DATA_DIR, DB_PATH, LEGACY_DB_PATH
from gos.modulos.ralenti.models import RalentiConfig, RalentiEvent, RalentiFile

DEFAULT_CONFIG = {"tolerancia": "5", "consumoLh": "3.5"}


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _loads(raw: str | None, default):
    try:
        return json.loads(raw or "")
    except (json.JSONDecodeError, TypeError):
        return default


def _ensure_default_config() -> None:
    for key, value in DEFAULT_CONFIG.items():
        if RalentiConfig.query.filter_by(key=key).first() is None:
            db.session.add(RalentiConfig(key=key, value=value))
    db.session.commit()


def migrate_legacy_data_if_empty() -> None:
    """Migra SQLite legacy de GOS Hs Ralenti si las tablas están vacías."""
    from flask import current_app

    if current_app.config.get("TESTING"):
        return
    _ensure_data_dir()
    _ensure_default_config()
    if RalentiFile.query.limit(1).first() is not None:
        return
    legacy = DB_PATH if DB_PATH.is_file() else LEGACY_DB_PATH
    if not legacy.is_file():
        return
    _migrate_sqlite(legacy)


def _migrate_sqlite(path) -> bool:
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        try:
            files = conn.execute("SELECT * FROM files ORDER BY imported_at").fetchall()
            if not files:
                return False
            for f in files:
                db.session.add(
                    RalentiFile(
                        name=f["name"],
                        imported_at=_parse_dt(f["imported_at"]) or datetime.utcnow(),
                        event_count=int(f["event_count"] or 0),
                        persons=f["persons"] or "[]",
                        marcha_totals=f["marcha_totals"] or "{}",
                        km_totals=f["km_totals"] or "{}",
                        ralenti_totals=_row_get(f, "ralenti_totals", "{}"),
                    )
                )
            events = conn.execute("SELECT * FROM events").fetchall()
            for e in events:
                db.session.add(
                    RalentiEvent(
                        file_name=e["file_name"],
                        persona=e["persona"] or "",
                        vehiculo=e["vehiculo"] or "",
                        referencia=e["referencia"] or "Sin referencia",
                        fecha=e["fecha"] or "",
                        mes=e["mes"] or "",
                        hora=int(e["hora"] or 0),
                        dur_min=float(e["dur_min"] or 0),
                        marcha_min=float(e["marcha_min"] or 0),
                        litros=float(e["litros"] or 0),
                    )
                )
            for row in conn.execute("SELECT key, value FROM config").fetchall():
                existing = RalentiConfig.query.filter_by(key=row["key"]).first()
                if existing:
                    existing.value = str(row["value"])
                else:
                    db.session.add(RalentiConfig(key=row["key"], value=str(row["value"])))
            db.session.commit()
            return True
        finally:
            conn.close()
    except Exception:
        db.session.rollback()
        raise


def _row_get(row, key: str, default: str) -> str:
    try:
        value = row[key]
        return value if value is not None else default
    except (IndexError, KeyError):
        return default


def _parse_dt(raw) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:26], fmt)
        except ValueError:
            continue
    return None


def list_files() -> list[dict]:
    rows = RalentiFile.query.order_by(RalentiFile.imported_at.desc()).all()
    result = []
    for row in rows:
        result.append(
            {
                "id": row.id,
                "name": row.name,
                "imported_at": row.imported_at.isoformat(sep=" ") if row.imported_at else "",
                "event_count": row.event_count or 0,
                "persons": _loads(row.persons, []),
                "marcha_totals": _loads(row.marcha_totals, {}),
                "km_totals": _loads(row.km_totals, {}),
                "ralenti_totals": _loads(row.ralenti_totals, {}),
            }
        )
    return result


def import_file(
    name: str,
    events: list[dict],
    persons: list | None = None,
    marcha_totals: dict | None = None,
    km_totals: dict | None = None,
    ralenti_totals: dict | None = None,
) -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("Nombre de archivo vacío")

    existing = RalentiFile.query.filter_by(name=name).first()
    if existing:
        RalentiEvent.query.filter_by(file_name=name).delete()
        db.session.delete(existing)
        db.session.flush()

    file_row = RalentiFile(
        name=name,
        event_count=len(events),
        persons=json.dumps(persons or [], ensure_ascii=False),
        marcha_totals=json.dumps(marcha_totals or {}, ensure_ascii=False),
        km_totals=json.dumps(km_totals or {}, ensure_ascii=False),
        ralenti_totals=json.dumps(ralenti_totals or {}, ensure_ascii=False),
    )
    db.session.add(file_row)
    db.session.flush()

    for e in events:
        db.session.add(
            RalentiEvent(
                file_name=name,
                persona=str(e.get("persona") or ""),
                vehiculo=str(e.get("vehiculo") or ""),
                referencia=str(e.get("referencia") or "Sin referencia"),
                fecha=str(e.get("fecha") or ""),
                mes=str(e.get("mes") or ""),
                hora=int(e.get("hora") or 0),
                dur_min=float(e.get("dur_min") or 0),
                marcha_min=float(e.get("marcha_min") or 0),
                litros=float(e.get("litros") or 0),
            )
        )
    db.session.commit()
    return {"ok": True, "name": name, "events": len(events)}


def delete_file(filename: str) -> None:
    row = RalentiFile.query.filter_by(name=filename).first()
    if not row:
        return
    RalentiEvent.query.filter_by(file_name=filename).delete()
    db.session.delete(row)
    db.session.commit()


def list_events(
    vehiculo: str | None = None,
    persona: str | None = None,
    mes: str | None = None,
    referencia: str | None = None,
) -> list[dict]:
    q = RalentiEvent.query
    if vehiculo:
        q = q.filter_by(vehiculo=vehiculo)
    if persona:
        q = q.filter_by(persona=persona)
    if mes:
        q = q.filter_by(mes=mes)
    if referencia:
        q = q.filter_by(referencia=referencia)
    rows = q.all()
    return [
        {
            "id": row.id,
            "file_name": row.file_name,
            "persona": row.persona,
            "vehiculo": row.vehiculo or "",
            "referencia": row.referencia or "Sin referencia",
            "fecha": row.fecha or "",
            "mes": row.mes or "",
            "hora": row.hora or 0,
            "dur_min": row.dur_min or 0,
            "marcha_min": row.marcha_min or 0,
            "litros": row.litros or 0,
        }
        for row in rows
    ]


def event_filters() -> dict:
    def distinct(column):
        rows = (
            db.session.query(column)
            .filter(column.isnot(None), column != "")
            .distinct()
            .order_by(column)
            .all()
        )
        return [r[0] for r in rows]

    return {
        "vehiculos": distinct(RalentiEvent.vehiculo),
        "personas": distinct(RalentiEvent.persona),
        "meses": distinct(RalentiEvent.mes),
        "referencias": distinct(RalentiEvent.referencia),
    }


def get_config() -> dict:
    _ensure_default_config()
    rows = RalentiConfig.query.all()
    result = {}
    for row in rows:
        try:
            result[row.key] = float(row.value)
        except (TypeError, ValueError):
            result[row.key] = row.value
    return result


def update_config(data: dict) -> None:
    for key, value in data.items():
        if not key:
            continue
        row = RalentiConfig.query.filter_by(key=str(key)).first()
        if row:
            row.value = str(value)
        else:
            db.session.add(RalentiConfig(key=str(key), value=str(value)))
    db.session.commit()


def reset_for_tests() -> None:
    RalentiEvent.query.delete()
    RalentiFile.query.delete()
    RalentiConfig.query.delete()
    db.session.commit()
