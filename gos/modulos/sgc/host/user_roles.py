"""Roles legacy QDV usados por organigrama / perfiles documentales SGC.

En GOS los roles de plataforma son distintos; estas constantes sirven para
etiquetas del organigrama y cobertura documental, sin tocar otras tablas.
"""

from __future__ import annotations

from typing import Any

ROLE_ADMINISTRADOR = "administrador"
ROLE_ADMINISTRACION = "administracion"
ROLE_LABORATORISTA = "laboratorista"
ROLE_LOGISTICA = "logistica"
ROLE_MANTENIMIENTO = "mantenimiento"
ROLE_MANTENIMIENTO_OPERACIONES = "mantenimiento_operaciones"
ROLE_OPERACIONES = "operaciones"
ROLE_SGI = "sgi"
ROLE_SOLO_LECTURA_TOTAL = "solo_lectura_total"

ROLE_LABELS: dict[str, str] = {
    ROLE_ADMINISTRADOR: "Administrador",
    ROLE_ADMINISTRACION: "Administración",
    ROLE_LABORATORISTA: "Laboratorista",
    ROLE_LOGISTICA: "Logística",
    ROLE_MANTENIMIENTO: "Mantenimiento",
    ROLE_MANTENIMIENTO_OPERACIONES: "Mantenimiento / Operaciones",
    ROLE_OPERACIONES: "Operaciones",
    ROLE_SGI: "SGC",
    ROLE_SOLO_LECTURA_TOTAL: "Solo lectura",
    "angel": "Ángel",
    "usuario": "Usuario",
    "cliente": "Cliente",
    "admin": "Administrador",
    "gerente": "Ángel",
    "responsable": "Ángel",
    "consulta": "Cliente",
    "sgc": "SGC",
}

_ALIASES = {
    "admin": ROLE_ADMINISTRADOR,
    "administrador": ROLE_ADMINISTRADOR,
    "sgc": ROLE_SGI,
    "sgi": ROLE_SGI,
    "consulta": ROLE_SOLO_LECTURA_TOTAL,
    "cliente": ROLE_SOLO_LECTURA_TOTAL,
}


def normalize_stored_rol(raw: Any) -> str:
    s = (str(raw) if raw is not None else "").strip().lower()
    if not s:
        return ""
    return _ALIASES.get(s, s)


def role_label(raw: Any) -> str:
    key = normalize_stored_rol(raw)
    return ROLE_LABELS.get(key, (str(raw) if raw is not None else "").strip() or key)


def role_covers_perfiles(raw: Any) -> set[str]:
    """Conjunto de perfiles documentales que cubre un rol de usuario."""
    role = normalize_stored_rol(raw)
    if not role:
        return set()
    if role in {ROLE_ADMINISTRADOR, "angel", "gerente", "responsable"}:
        return {
            ROLE_OPERACIONES,
            ROLE_LOGISTICA,
            ROLE_ADMINISTRACION,
            ROLE_MANTENIMIENTO,
            ROLE_MANTENIMIENTO_OPERACIONES,
            ROLE_SGI,
            ROLE_SOLO_LECTURA_TOTAL,
        }
    if role == ROLE_SGI:
        return {ROLE_SGI, ROLE_SOLO_LECTURA_TOTAL}
    return {role}


def user_is_global_read_only(user: Any) -> bool:
    if user is None:
        return True
    if getattr(user, "es_solo_lectura", lambda: False)():
        return True
    role = normalize_stored_rol(getattr(user, "rol", None))
    return role in {ROLE_SOLO_LECTURA_TOTAL, "cliente", "consulta", "usuario"}
