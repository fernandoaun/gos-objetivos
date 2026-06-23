import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from app.config import BASE_DIR, config_by_name
from app.extensions import db, login_manager, migrate

STATIC_DIR = BASE_DIR / "static"


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv()
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(Path(__file__).resolve().parent / "templates"),
        static_folder=str(STATIC_DIR),
        static_url_path="/static",
    )

    env = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(env, config_by_name["development"]))

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import (  # noqa: F401 — registrar tablas
        Area,
        Empresa,
        FodaDocumento,
        FodaItem,
        DafoTarea,
        KpiIndicador,
        Objetivo,
        PlaneamientoConfig,
        Responsable,
        Sector,
        Usuario,
    )

    if not app.config.get("TESTING"):
        with app.app_context():
            db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    _register_blueprints(app)
    _register_auto_login(app)

    @app.context_processor
    def inject_nav():
        from flask import request
        from flask_login import current_user

        from app.models.kpi import (
            KPI_TIPO_MEDICION_LABELS,
            KPI_TIPO_MEDICION_OPCIONES,
            KPI_TIPO_MEDICION_TITULOS,
        )
        from app.version import APP_VERSION, APP_VERSION_LABEL

        puede_editar_kpi = (
            current_user.is_authenticated
            and getattr(current_user, "rol", None) in ("admin", "gerente", "responsable")
        )

        return {
            "nav_items": _nav_items(),
            "current_endpoint": request.endpoint or "",
            "app_version": APP_VERSION,
            "app_version_label": APP_VERSION_LABEL,
            "tipo_medicion_opciones": KPI_TIPO_MEDICION_OPCIONES,
            "tipo_medicion_labels": KPI_TIPO_MEDICION_LABELS,
            "tipo_medicion_titulos": KPI_TIPO_MEDICION_TITULOS,
            "kpi_editable": puede_editar_kpi,
        }

    return app


def _register_auto_login(app: Flask) -> None:
    if not app.config.get("AUTO_LOGIN"):
        return

    from flask import request
    from flask_login import current_user, login_user

    from app.services import auth_service

    @app.before_request
    def _auto_login():
        if request.endpoint == "static":
            return
        if current_user.is_authenticated:
            return
        user = auth_service.obtener_o_crear_usuario_default()
        login_user(user, remember=True)


def _nav_items():
    return [
        {"label": "Dashboard", "endpoint": "dashboard.index", "icon": "bi-speedometer2"},
        {"label": "FODA", "endpoint": "foda.index", "icon": "bi-grid-3x3-gap"},
        {"label": "Objetivos Estratégicos", "endpoint": "objetivos.index", "icon": "bi-bullseye"},
        {"label": "KPI", "endpoint": "kpis.index", "icon": "bi-graph-up"},
        {"label": "Reportes", "endpoint": "reportes.index", "icon": "bi-file-earmark-bar-graph"},
        {"label": "Configuración", "endpoint": "configuracion.index", "icon": "bi-gear"},
    ]


def _register_blueprints(app: Flask) -> None:
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.configuracion import bp as config_bp
    from app.blueprints.dashboard import bp as dashboard_bp
    from app.blueprints.foda import bp as foda_bp
    from app.blueprints.kpis import bp as kpis_bp
    from app.blueprints.main import bp as main_bp
    from app.blueprints.metas import bp as metas_bp
    from app.blueprints.objetivos import bp as objetivos_bp
    from app.blueprints.planes import bp as planes_bp
    from app.blueprints.api import bp as api_bp
    from app.blueprints.reportes import bp as reportes_bp
    from app.blueprints.seguimiento import bp as seguimiento_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(foda_bp, url_prefix="/foda")
    app.register_blueprint(objetivos_bp, url_prefix="/objetivos")
    app.register_blueprint(metas_bp, url_prefix="/metas")
    app.register_blueprint(kpis_bp, url_prefix="/kpis")
    app.register_blueprint(seguimiento_bp, url_prefix="/seguimiento")
    app.register_blueprint(planes_bp, url_prefix="/planes-accion")
    app.register_blueprint(reportes_bp, url_prefix="/reportes")
    app.register_blueprint(config_bp, url_prefix="/configuracion")
