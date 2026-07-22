"""Asegura tablas del módulo Mantenimiento."""

from gos.extensions import db


def ensure_mantenimiento_schema() -> None:
    from gos.modulos.mantenimiento.models import (  # noqa: F401
        MantPlanCelda,
        MantPlanMeta,
        MantUnidad,
        MantVtv,
    )

    db.create_all()
