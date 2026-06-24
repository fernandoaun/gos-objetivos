import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from gos.config import config_by_name
from gos.extensions import db, login_manager, migrate

GOS_DIR = Path(__file__).resolve().parent
STATIC_DIR = GOS_DIR / "static"
TEMPLATES_DIR = GOS_DIR / "templates"


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv()
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
        static_url_path="/static",
    )

    env = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(env, config_by_name["development"]))

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from gos.models import Empresa, Usuario  # noqa: F401

    if not app.config.get("TESTING"):
        with app.app_context():
            try:
                _bootstrap_database()
            except Exception:
                app.logger.exception(
                    "No se pudo inicializar la base al arrancar; el servicio sigue activo."
                )

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    _register_core_blueprints(app)
    _register_modules(app)
    _register_auto_login(app)

    @app.context_processor
    def inject_platform():
        from flask import request

        from gos.version import APP_VERSION, APP_VERSION_LABEL

        modules = []
        with app.app_context():
            from gos.modulos.objetivos import module_descriptor

            modules.append(module_descriptor())

        current_module = ""
        if request.path.startswith("/gos/objetivos"):
            current_module = "objetivos"

        return {
            "gos_modules": modules,
            "current_module": current_module,
            "app_version": APP_VERSION,
            "app_version_label": APP_VERSION_LABEL,
        }

    return app


def _bootstrap_database() -> None:
    from gos.models import Empresa, Usuario  # noqa: F401
    from gos.services.bootstrap_service import ensure_initial_admin
    from gos.modulos.objetivos import ensure_planeamiento_config

    db.create_all()
    ensure_initial_admin()
    ensure_planeamiento_config()


def _register_core_blueprints(app: Flask) -> None:
    from gos.blueprints.auth import bp as auth_bp
    from gos.blueprints.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")


def _register_modules(app: Flask) -> None:
    from gos.modulos.objetivos import register as register_objetivos

    register_objetivos(app)


def _register_auto_login(app: Flask) -> None:
    if not app.config.get("AUTO_LOGIN"):
        return

    from flask import request
    from flask_login import current_user, login_user

    from gos.services import auth_service

    @app.before_request
    def _auto_login():
        if request.endpoint in ("static", "objetivos_static.static"):
            return
        if current_user.is_authenticated:
            return
        user = auth_service.obtener_o_crear_usuario_default()
        login_user(user, remember=True)
