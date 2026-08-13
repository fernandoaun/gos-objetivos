from pathlib import Path

from flask import Blueprint, Flask
from jinja2 import ChoiceLoader, FileSystemLoader

MODULE_DIR = Path(__file__).resolve().parent
MODULE_NAME = "sgc"
URL_PREFIX = "/gos/sgc"


def register(app: Flask, url_prefix: str = URL_PREFIX) -> None:
    _ensure_template_loader(app)
    _register_models()
    with app.app_context():
        _upgrade_schema()
    _register_blueprints(app, url_prefix)
    _register_context(app)


def _upgrade_schema() -> None:
    from gos.modulos.sgc.schema_upgrade import ensure_sgc_schema

    ensure_sgc_schema()


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


def _register_models() -> None:
    import gos.modulos.sgc.models  # noqa: F401


def _register_blueprints(app: Flask, url_prefix: str) -> None:
    from gos.modulos.sgc.blueprints import bp as sgi_bp

    static_bp = Blueprint(
        "sgc_static",
        __name__,
        static_folder=str(MODULE_DIR / "static"),
        static_url_path=f"{url_prefix}/static",
    )
    app.register_blueprint(static_bp)
    # Blueprint interno se llama "sgi" (rutas/templates QDV); prefix GOS.
    app.register_blueprint(sgi_bp, url_prefix=url_prefix)


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_sgc_nav():
        from flask import request

        if not request.path.startswith(URL_PREFIX):
            return {}
        return {
            "nav_items": _nav_items(),
            "current_endpoint": request.endpoint or "",
            "current_module": MODULE_NAME,
            "module_nav_label": "SGC",
        }


def module_descriptor() -> dict:
    return {
        "code": MODULE_NAME,
        "label": "SGC",
        "description": "Sistema de Gestión de la Calidad: procedimientos, manuales y registros.",
        "icon": "bi-journal-check",
        "url": f"{URL_PREFIX}/",
    }


def _nav_items():
    return [
        {"label": "Hub SGC", "endpoint": "sgi.hub", "icon": "bi-house"},
    ]
