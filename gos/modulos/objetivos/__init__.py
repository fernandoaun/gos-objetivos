from pathlib import Path

from flask import Blueprint, Flask, url_for

MODULE_DIR = Path(__file__).resolve().parent
MODULE_NAME = "objetivos"
URL_PREFIX = "/gos/objetivos"


def register(app: Flask, url_prefix: str = URL_PREFIX) -> None:
    _ensure_template_loader(app)
    _register_models()
    _register_blueprints(app, url_prefix)
    _register_context(app)


def _ensure_template_loader(app: Flask) -> None:
    from jinja2 import ChoiceLoader, FileSystemLoader

    objetivos_templates = str(MODULE_DIR / "templates")
    existing = app.jinja_loader
    loaders = []
    if isinstance(existing, ChoiceLoader):
        loaders.extend(existing.loaders)
    elif existing is not None:
        loaders.append(existing)
    loaders.append(FileSystemLoader(objetivos_templates))
    app.jinja_loader = ChoiceLoader(loaders)


def _register_models() -> None:
    from gos.modulos.objetivos.models import (  # noqa: F401
        Area,
        DafoTarea,
        FodaDocumento,
        FodaItem,
        KpiIndicador,
        Objetivo,
        PlaneamientoConfig,
        Responsable,
        Sector,
    )


def _register_blueprints(app: Flask, url_prefix: str) -> None:
    from gos.modulos.objetivos.blueprints.api import bp as api_bp
    from gos.modulos.objetivos.blueprints.configuracion import bp as config_bp
    from gos.modulos.objetivos.blueprints.dashboard import bp as dashboard_bp
    from gos.modulos.objetivos.blueprints.foda import bp as foda_bp
    from gos.modulos.objetivos.blueprints.kpis import bp as kpis_bp
    from gos.modulos.objetivos.blueprints.main import bp as main_bp
    from gos.modulos.objetivos.blueprints.metas import bp as metas_bp
    from gos.modulos.objetivos.blueprints.objetivos import bp as estrategicos_bp
    from gos.modulos.objetivos.blueprints.planes import bp as planes_bp
    from gos.modulos.objetivos.blueprints.reportes import bp as reportes_bp
    from gos.modulos.objetivos.blueprints.seguimiento import bp as seguimiento_bp

    static_bp = Blueprint(
        "objetivos_static",
        __name__,
        static_folder=str(MODULE_DIR / "static"),
        static_url_path=f"{url_prefix}/static",
    )

    app.register_blueprint(static_bp)
    app.register_blueprint(main_bp, url_prefix=url_prefix)
    app.register_blueprint(api_bp, url_prefix=f"{url_prefix}/api/v1")
    app.register_blueprint(dashboard_bp, url_prefix=f"{url_prefix}/dashboard")
    app.register_blueprint(foda_bp, url_prefix=f"{url_prefix}/foda")
    app.register_blueprint(estrategicos_bp, url_prefix=f"{url_prefix}/objetivos")
    app.register_blueprint(metas_bp, url_prefix=f"{url_prefix}/metas")
    app.register_blueprint(kpis_bp, url_prefix=f"{url_prefix}/kpis")
    app.register_blueprint(seguimiento_bp, url_prefix=f"{url_prefix}/seguimiento")
    app.register_blueprint(planes_bp, url_prefix=f"{url_prefix}/planes-accion")
    app.register_blueprint(reportes_bp, url_prefix=f"{url_prefix}/reportes")
    app.register_blueprint(config_bp, url_prefix=f"{url_prefix}/configuracion")


def _register_context(app: Flask) -> None:
    @app.context_processor
    def inject_objetivos_nav():
        from flask import request

        if not request.path.startswith(URL_PREFIX):
            return {}

        from flask_login import current_user

        from gos.modulos.objetivos.models.kpi import (
            KPI_TIPO_MEDICION_LABELS,
            KPI_TIPO_MEDICION_OPCIONES,
            KPI_TIPO_MEDICION_TITULOS,
        )
        from gos.modulos.objetivos.version import APP_VERSION, APP_VERSION_LABEL

        puede_editar_kpi = (
            current_user.is_authenticated
            and getattr(current_user, "rol", None) in ("admin", "gerente", "responsable")
        )

        return {
            "nav_items": _nav_items(),
            "current_endpoint": request.endpoint or "",
            "current_module": MODULE_NAME,
            "module_nav_label": "Objetivos",
            "app_version": APP_VERSION,
            "app_version_label": APP_VERSION_LABEL,
            "tipo_medicion_opciones": KPI_TIPO_MEDICION_OPCIONES,
            "tipo_medicion_labels": KPI_TIPO_MEDICION_LABELS,
            "tipo_medicion_titulos": KPI_TIPO_MEDICION_TITULOS,
            "kpi_editable": puede_editar_kpi,
        }


def module_descriptor():
    return {
        "code": MODULE_NAME,
        "label": "Objetivos",
        "description": "Planeamiento estratégico: FODA, objetivos, metas y KPI.",
        "icon": "bi-bullseye",
        "url": "/gos/objetivos/dashboard/",
    }


def _nav_items():
    return [
        {"label": "Dashboard", "endpoint": "objetivos_dashboard.index", "icon": "bi-speedometer2"},
        {"label": "FODA", "endpoint": "objetivos_foda.index", "icon": "bi-grid-3x3-gap"},
        {
            "label": "Objetivos Estratégicos",
            "endpoint": "objetivos_estrategicos.index",
            "icon": "bi-bullseye",
        },
        {"label": "KPI", "endpoint": "objetivos_kpis.index", "icon": "bi-graph-up"},
        {"label": "Reportes", "endpoint": "objetivos_reportes.index", "icon": "bi-file-earmark-bar-graph"},
        {"label": "Configuración", "endpoint": "objetivos_configuracion.index", "icon": "bi-gear"},
    ]


def ensure_planeamiento_config() -> None:
    from gos.extensions import db
    from gos.models import Empresa
    from gos.modulos.objetivos.models.catalogos import PlaneamientoConfig

    for empresa in Empresa.query.filter_by(activa=True).all():
        if PlaneamientoConfig.query.filter_by(empresa_id=empresa.id).first():
            continue
        db.session.add(PlaneamientoConfig(empresa_id=empresa.id))
    db.session.commit()
