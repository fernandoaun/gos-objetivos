"""Crea tablas sgi_* sin alterar tablas de otros módulos."""

from gos.extensions import db


def ensure_sgc_schema() -> None:
    import gos.modulos.sgc.models  # noqa: F401

    # Solo crea tablas faltantes; no modifica esquema existente de otros módulos.
    db.create_all()
