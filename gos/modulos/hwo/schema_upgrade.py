"""Ampliaciones de esquema HWO (modalidad con historial JSON)."""

from sqlalchemy import inspect, text

from gos.extensions import db


def ensure_hwo_schema() -> None:
    from gos.modulos.hwo.models import HwoDataset, HwoModalidad  # noqa: F401

    db.create_all()
    inspector = inspect(db.engine)
    if not inspector.has_table("hwo_modalidad"):
        return
    cols = {c["name"]: c for c in inspector.get_columns("hwo_modalidad")}
    col = cols.get("schedule")
    if not col:
        return
    type_str = str(col.get("type", "")).upper()
    if "TEXT" in type_str or "CLOB" in type_str:
        return
    if db.engine.dialect.name == "postgresql":
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE hwo_modalidad ALTER COLUMN schedule TYPE TEXT"))
