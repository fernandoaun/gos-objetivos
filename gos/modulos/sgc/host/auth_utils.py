"""Auth helpers SGC adaptados a Flask-Login + perfiles GOS."""

from __future__ import annotations

from typing import Any

from flask_login import current_user as flask_current_user
from flask_login import login_required  # noqa: F401

from gos.services.modulo_service import usuario_puede_acceder_modulo


def current_user():
    """API QDV: current_user() callable. En GOS es el proxy de Flask-Login."""
    u = flask_current_user
    if u is None or not getattr(u, "is_authenticated", False):
        return None
    return u


def user_display_name(user: Any) -> str:
    if user is None:
        return ""
    nombre = (getattr(user, "nombre", None) or getattr(user, "nombre_completo", None) or "").strip()
    if nombre:
        return nombre
    return (getattr(user, "email", None) or getattr(user, "username", None) or "").strip()


def _puede_sgc(user: Any) -> bool:
    if user is None:
        return False
    if getattr(user, "es_administrador", lambda: False)():
        return True
    if getattr(user, "es_angel", lambda: False)():
        return True
    return usuario_puede_acceder_modulo(user, "sgc")


def user_can_access_sgi(user: Any) -> bool:
    return _puede_sgc(user)


def user_can_edit_sgi_documentos(user: Any) -> bool:
    if user is None:
        return False
    if getattr(user, "es_administrador", lambda: False)():
        return True
    if getattr(user, "es_angel", lambda: False)():
        return True
    if getattr(user, "es_solo_lectura", lambda: False)():
        return False
    return usuario_puede_acceder_modulo(user, "sgc") and getattr(user, "puede_editar_operativa", lambda: False)()


def user_can_delete_sgi_documentos(user: Any) -> bool:
    if user is None:
        return False
    if getattr(user, "es_administrador", lambda: False)():
        return True
    rol = (getattr(user, "rol", None) or "").strip().lower()
    return rol in {"sgi", "sgc", "administrador", "admin", "angel", "gerente", "responsable"}


def user_can_asociar_sgi_registro_modulo(user: Any) -> bool:
    return user_can_delete_sgi_documentos(user)


def user_can_create_sgi_digital_record(user: Any) -> bool:
    return user_can_asociar_sgi_registro_modulo(user)


def user_can_manage_sgi_record_entries(user: Any) -> bool:
    return user_can_access_sgi(user)


def user_can_view_sgi_obsoletos(user: Any) -> bool:
    return user_can_access_sgi(user)


def user_can(user: Any, permission: str) -> bool:
    if permission in {"sgi_hub", "sgc"}:
        return user_can_access_sgi(user)
    if permission == "sgi_documentos_edit":
        return user_can_edit_sgi_documentos(user)
    return False


def user_can_edit(user: Any, permission: str) -> bool:
    return user_can(user, permission)
