"""Asegura tablas/columnas del módulo Recursos."""

from sqlalchemy import inspect, text

from gos.extensions import db

_COLUMN_UPGRADES = [
    ("rec_unidades", "es_centro", "BOOLEAN DEFAULT 0"),
]


def ensure_recursos_schema() -> None:
    from gos.modulos.recursos.models import (  # noqa: F401
        RecAsignacion,
        RecCambio,
        RecCentro,
        RecCupo,
        RecDestino,
        RecUnidad,
    )

    db.create_all()
    inspector = inspect(db.engine)
    for table, column, coldef in _COLUMN_UPGRADES:
        if not inspector.has_table(table):
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column in existing:
            continue
        with db.engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coldef}"))
    _backfill_centros()


def _backfill_centros() -> None:
    from gos.modulos.recursos.models import RecCentro, RecDestino

    inspector = inspect(db.engine)
    if not inspector.has_table("rec_centros") or not inspector.has_table("rec_destinos"):
        return
    existentes = {
        c.codigo: c for c in db.session.execute(db.select(RecCentro)).scalars().all()
    }
    destinos = list(db.session.execute(db.select(RecDestino)).scalars().all())
    for dest in destinos:
        equipo = (dest.equipo or "").strip()
        if not equipo or equipo.upper() == "GOS" or dest.grupo != "servicio":
            continue
        centro = existentes.get(equipo)
        if centro is None:
            centro = RecCentro(
                codigo=equipo,
                nombre=equipo,
                destino_id=dest.id if dest.activo else None,
                activo=True,
            )
            db.session.add(centro)
            existentes[equipo] = centro
        elif dest.activo and centro.destino_id is None:
            centro.destino_id = dest.id
    db.session.commit()
