"""Asegura tablas del módulo O&M."""

from gos.extensions import db


def ensure_om_schema() -> None:
    from gos.modulos.om.models import (  # noqa: F401
        OmAuditLog,
        OmItem,
        OmModule,
        OmPersonnel,
        OmPhone,
    )

    db.create_all()
