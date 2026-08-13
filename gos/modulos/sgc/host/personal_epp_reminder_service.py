"""Stub: GOS no tiene módulo Personal QDV; usa email del legajo stub si existe."""

from __future__ import annotations

from typing import Any

from gos.modulos.sgc.host.deadline_alert_email_service import normalize_validate_email


def resolve_empleado_email(emp: Any) -> str | None:
    if emp is None:
        return None
    for attr in ("email", "mail", "correo"):
        val = getattr(emp, attr, None)
        norm = normalize_validate_email(val)
        if norm:
            return norm
    return None
