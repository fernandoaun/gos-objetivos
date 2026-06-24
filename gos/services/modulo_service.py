"""Filtrado de módulos visibles según el rol del usuario."""

from flask_login import AnonymousUserMixin


def modulos_para_usuario(user, descriptors: list[dict]) -> list[dict]:
    if isinstance(user, AnonymousUserMixin) or not user.is_authenticated:
        return descriptors

    if user.es_administrador() or user.es_angel():
        return descriptors

    if user.es_usuario():
        return [d for d in descriptors if d.get("code") == "capacitacion"]

    # Cliente: acceso de lectura a todos los módulos para presentar información
    return descriptors
