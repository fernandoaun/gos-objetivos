"""Filtrado de módulos visibles según perfil o rol del usuario."""

from flask_login import AnonymousUserMixin

MODULO_CODES = ("objetivos", "capacitacion", "hwo", "vacaciones")

MODULO_LABELS = {
    "objetivos": "Objetivos",
    "capacitacion": "Capacitación",
    "hwo": "Análisis",
    "vacaciones": "Vacaciones",
}


def _modulos_por_rol(user) -> set[str] | None:
    if user.es_angel():
        return None
    if user.es_usuario():
        return {"capacitacion"}
    if user.es_cliente():
        return None
    return set()


def codigos_modulos_permitidos(user) -> set[str] | None:
    """Devuelve los códigos permitidos. None significa acceso a todos los módulos."""
    if isinstance(user, AnonymousUserMixin) or not user.is_authenticated:
        return set()

    if user.es_administrador():
        return None

    if user.perfil_id and user.perfil:
        return set(user.perfil.modulos or [])

    return _modulos_por_rol(user)


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
    if path.startswith("/gos/objetivos"):
        return "objetivos"
    if path.startswith("/gos/capacitacion"):
        return "capacitacion"
    if path.startswith("/gos/hwo"):
        return "hwo"
    if path.startswith("/gos/vacaciones"):
        return "vacaciones"
    return None
