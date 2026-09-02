"""Filtrado de módulos visibles según perfil o rol del usuario."""

from flask_login import AnonymousUserMixin

MODULO_CODES = (
    "dashboard",
    "objetivos",
    "capacitacion",
    "hwo",
    "vacaciones",
    "ralenti",
    "mantenimiento",
    "om",
    "recursos",
    "sgc",
)

MODULO_LABELS = {
    "dashboard": "DashBoard",
    "objetivos": "Objetivos",
    "capacitacion": "Capacitación",
    "hwo": "Análisis",
    "vacaciones": "Vacaciones",
    "ralenti": "Ralentí",
    "mantenimiento": "Mantenimiento",
    "om": "O&M",
    "recursos": "Recursos",
    "sgc": "SGC",
}

_OBJETIVOS_CODES = (
    "dashboard",
    "objetivos",
    "hwo",
    "vacaciones",
    "ralenti",
    "mantenimiento",
    "om",
    "recursos",
    "sgc",
)


def modulo_codes_activos() -> tuple[str, ...]:
    """Códigos disponibles en el programa actual (GOS_APP_MODE)."""
    try:
        from gos import env
        from gos.app_mode import capacitacion_enabled, objetivos_stack_enabled

        mode = env.app_mode()
    except Exception:
        return MODULO_CODES

    if mode == "capacitacion":
        return ("capacitacion",)
    if mode == "objetivos":
        return _OBJETIVOS_CODES
    return MODULO_CODES


def _modulos_por_rol(user) -> set[str] | None:
    if user.es_angel():
        return None
    if user.es_usuario():
        activos = set(modulo_codes_activos())
        if "capacitacion" in activos:
            return {"capacitacion"}
        return set()
    if user.es_cliente():
        return None
    return set()


def codigos_modulos_permitidos(user) -> set[str] | None:
    """Devuelve los códigos permitidos. None significa acceso a todos los módulos."""
    if isinstance(user, AnonymousUserMixin) or not user.is_authenticated:
        return set()

    activos = set(modulo_codes_activos())

    if user.es_administrador():
        return None

    if user.perfil_id and user.perfil:
        return set(user.perfil.modulos or []) & activos

    rol = _modulos_por_rol(user)
    if rol is None:
        return None
    return rol & activos


def modulos_para_usuario(user, descriptors: list[dict]) -> list[dict]:
    permitidos = codigos_modulos_permitidos(user)
    if permitidos is None:
        return descriptors
    return [d for d in descriptors if d.get("code") in permitidos]


def usuario_puede_acceder_modulo(user, code: str) -> bool:
    permitidos = codigos_modulos_permitidos(user)
    if permitidos is None:
        return True
    return code in permitidos


def modulo_desde_ruta(path: str) -> str | None:
    if path.startswith("/gos/dashboard"):
        return "dashboard"
    if path.startswith("/gos/objetivos"):
        return "objetivos"
    if path.startswith("/gos/capacitacion"):
        return "capacitacion"
    if path.startswith("/gos/hwo"):
        return "hwo"
    if path.startswith("/gos/vacaciones"):
        return "vacaciones"
    if path.startswith("/gos/ralenti"):
        return "ralenti"
    if path.startswith("/gos/mantenimiento"):
        return "mantenimiento"
    if path.startswith("/gos/om"):
        return "om"
    if path.startswith("/gos/recursos"):
        return "recursos"
    if path.startswith("/gos/sgc"):
        return "sgc"
    return None
