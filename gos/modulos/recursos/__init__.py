from pathlib import Path

from flask import Blueprint, Flask
from jinja2 import ChoiceLoader, FileSystemLoader

MODULE_DIR = Path(__file__).resolve().parent
MODULE_NAME = "recursos"
URL_PREFIX = "/gos/recursos"


def register(app: Flask, url_prefix: str = URL_PREFIX) -> None:
    _ensure_template_loader(app)
    with app.app_context():
        from gos.modulos.recursos.schema_upgrade import ensure_recursos_schema

        ensure_recursos_schema()
    _register_blueprints(app, url_prefix)
    _register_context(app)


def _ensure_template_loader(app: Flask) -> None:
    templates = str(MODULE_DIR / "templates")
    existing = app.jinja_loader
    loaders = []
    if isinstance(existing, ChoiceLoader):
        loaders.extend(existing.loaders)
    elif existing is not None:
        loaders.append(existing)
    loaders.append(FileSystemLoader(templates))
    app.jinja_loader = ChoiceLoader(loaders)


def _register_blueprints(app: Flask, url_prefix: str) -> None:
    from gos.modulos.recursos.blueprints.api import bp as api_bp
    from gos.modulos.recursos.blueprints.main import bp as main_bp

    static_bp = Blueprint(
        "recursos_static",
        __name__,
        static_folder=str(MODULE_DIR / "static"),
        static_url_path=f"{url_prefix}/static",
    )

    app.register_blueprint(static_bp)
    app.register_blueprint(main_bp, url_prefix=url_prefix)
    app.register_blueprint(api_bp, url_prefix=f"{url_prefix}/api")


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_recursos_nav():
        from flask import request

        if not request.path.startswith(URL_PREFIX):
            return {}

        return {
            "nav_items": _nav_items(),
            "current_endpoint": request.endpoint or "",
            "current_module": MODULE_NAME,
            "module_nav_label": "Recursos",
        }


def module_descriptor() -> dict:
    return {
        "code": MODULE_NAME,
        "label": "Recursos",
        "description": "Afectación de unidades por servicio y estructura operativa.",
        "icon": "bi-truck",
        "url": "/gos/recursos/",
    }


def _nav_items():
    return [
        {
            "label": "Tablero",
            "endpoint": "recursos_main.index",
            "icon": "bi-speedometer2",
        },
        {
            "label": "Flota",
            "endpoint": "recursos_main.flota",
            "icon": "bi-list-ul",
        },
        {
            "label": "Servicios",
            "endpoint": "recursos_main.servicios",
            "icon": "bi-diagram-3",
        },
        {
            "label": "Centros",
            "endpoint": "recursos_main.centros",
            "icon": "bi-geo-alt",
        },
        {
            "label": "Importar",
            "endpoint": "recursos_main.importar",
            "icon": "bi-upload",
        },
    ]
