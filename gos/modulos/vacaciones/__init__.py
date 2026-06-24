from pathlib import Path

from flask import Flask
from jinja2 import ChoiceLoader, FileSystemLoader

MODULE_DIR = Path(__file__).resolve().parent
MODULE_NAME = "vacaciones"
URL_PREFIX = "/gos/vacaciones"


def register(app: Flask, url_prefix: str = URL_PREFIX) -> None:
    _ensure_template_loader(app)
    from gos.modulos.vacaciones.database import init_db, migrate_legacy_data_if_empty

    init_db()
    migrate_legacy_data_if_empty()
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
    from gos.modulos.vacaciones.blueprints.api import bp as api_bp
    from gos.modulos.vacaciones.blueprints.main import bp as main_bp

    app.register_blueprint(main_bp, url_prefix=url_prefix)
    app.register_blueprint(api_bp, url_prefix=f"{url_prefix}/api")


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_vacaciones_nav():
        from flask import request

        if not request.path.startswith(URL_PREFIX):
            return {}

        return {
            "nav_items": _nav_items(),
            "current_endpoint": request.endpoint or "",
            "current_module": MODULE_NAME,
            "module_nav_label": "Vacaciones",
        }


def module_descriptor() -> dict:
    return {
        "code": MODULE_NAME,
        "label": "Vacaciones",
        "description": "Control de vacaciones adeudadas: planilla vs registros TOTAL.",
        "icon": "bi-sun",
        "url": "/gos/vacaciones/",
    }


def _nav_items():
    return [
        {
            "label": "Vacaciones adeudadas",
            "endpoint": "vacaciones_main.index",
            "icon": "bi-calendar-check",
        },
        {
            "label": "Importar datos",
            "endpoint": "vacaciones_main.importar",
            "icon": "bi-upload",
        },
    ]
