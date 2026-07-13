from pathlib import Path

from flask import Blueprint, Flask
from jinja2 import ChoiceLoader, FileSystemLoader

MODULE_DIR = Path(__file__).resolve().parent
MODULE_NAME = "ralenti"
URL_PREFIX = "/gos/ralenti"


def register(app: Flask, url_prefix: str = URL_PREFIX) -> None:
    _ensure_template_loader(app)
    with app.app_context():
        try:
            from gos.modulos.ralenti.storage import migrate_legacy_data_if_empty

            migrate_legacy_data_if_empty()
        except Exception:
            app.logger.exception("No se pudo migrar datos legacy de Ralentí")
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
    from gos.modulos.ralenti.blueprints.api import bp as api_bp
    from gos.modulos.ralenti.blueprints.main import bp as main_bp

    static_bp = Blueprint(
        "ralenti_static",
        __name__,
        static_folder=str(MODULE_DIR / "static"),
        static_url_path=f"{url_prefix}/static",
    )

    app.register_blueprint(static_bp)
    app.register_blueprint(main_bp, url_prefix=url_prefix)
    app.register_blueprint(api_bp, url_prefix=f"{url_prefix}/api")


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_ralenti_nav():
        from flask import request

        if not request.path.startswith(URL_PREFIX):
            return {}

        return {
            "nav_items": _nav_items(),
            "current_endpoint": request.endpoint or "",
            "current_module": MODULE_NAME,
            "module_nav_label": "Ralentí",
        }


def module_descriptor() -> dict:
    return {
        "code": MODULE_NAME,
        "label": "Ralentí",
        "description": "Horas de ralentí, consumo y compliance por unidad.",
        "icon": "bi-speedometer2",
        "url": "/gos/ralenti/",
    }


def _nav_items():
    return [
        {
            "label": "Dashboard",
            "endpoint": "ralenti_main.index",
            "icon": "bi-speedometer2",
        },
    ]
