"""Compatibilidad temporal: redirige al paquete principal GOS."""
from gos import create_app
from gos.config import BASE_DIR, config_by_name
from gos.extensions import db, login_manager, migrate

__all__ = ["create_app", "BASE_DIR", "config_by_name", "db", "login_manager", "migrate"]
