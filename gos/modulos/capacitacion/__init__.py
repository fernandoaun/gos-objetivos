from pathlib import Path

from flask import Blueprint, Flask
from jinja2 import ChoiceLoader, FileSystemLoader

MODULE_DIR = Path(__file__).resolve().parent
MODULE_NAME = "capacitacion"
URL_PREFIX = "/gos/capacitacion"


def register(app: Flask, url_prefix: str = URL_PREFIX) -> None:
    _ensure_template_loader(app)
    _register_models()
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


def _register_models() -> None:
    from gos.modulos.capacitacion.models import (  # noqa: F401
        AsistenciaEncuentro,
        CertificacionEmpleado,
        CertificacionTipo,
        Curso,
        EncuentroCapacitacion,
        EncuentroTema,
        InscripcionPrograma,
        Participante,
        PlanCapacitacion,
        ProgramaCapacitacion,
        Puesto,
        RegistroCapacitacion,
        RequisitoFormacion,
    )


def _register_blueprints(app: Flask, url_prefix: str) -> None:
    from gos.modulos.capacitacion.blueprints.api import bp as api_bp
    from gos.modulos.capacitacion.blueprints.main import bp as main_bp

    static_bp = Blueprint(
        "capacitacion_static",
        __name__,
        static_folder=str(MODULE_DIR / "static"),
        static_url_path=f"{url_prefix}/static",
    )

    app.register_blueprint(static_bp)
    app.register_blueprint(main_bp, url_prefix=url_prefix)
    app.register_blueprint(api_bp, url_prefix=f"{url_prefix}/api")


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_capacitacion_nav():
        from flask import request

        if not request.path.startswith(URL_PREFIX):
            return {}

        return {
            "nav_items": _nav_items(),
            "current_endpoint": request.endpoint or "",
            "current_module": MODULE_NAME,
            "module_nav_label": "Capacitación",
        }


def module_descriptor() -> dict:
    return {
        "code": MODULE_NAME,
        "label": "Capacitación",
        "description": "Seguimiento de capacitaciones y certificaciones del personal.",
        "icon": "bi-mortarboard",
        "url": "/gos/capacitacion/",
    }


def _nav_items():
    return [
        {
            "label": "Panel",
            "endpoint": "capacitacion_main.index",
            "icon": "bi-speedometer2",
        },
        {
            "label": "Programas y encuentros",
            "endpoint": "capacitacion_main.programas",
            "icon": "bi-calendar-event",
        },
        {
            "label": "Personas",
            "endpoint": "capacitacion_main.personas",
            "icon": "bi-people",
        },
        {
            "label": "Catálogos",
            "endpoint": "capacitacion_main.catalogos",
            "icon": "bi-journal-bookmark",
        },
    ]
