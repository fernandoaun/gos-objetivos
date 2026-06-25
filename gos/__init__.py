import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from gos import env
from gos.config import apply_env_to_app, config_by_name
from gos.extensions import db, login_manager, migrate

GOS_DIR = Path(__file__).resolve().parent
STATIC_DIR = GOS_DIR / "static"
TEMPLATES_DIR = GOS_DIR / "templates"


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv()
    env_name = config_name or os.environ.get("FLASK_ENV", "development")
    env.set_runtime_env(env_name)
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
        static_url_path="/static",
    )

    app.config.from_object(config_by_name.get(env_name, config_by_name["development"]))
    apply_env_to_app(app)

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
        from flask_login import current_user

        from gos.services.modulo_service import modulos_para_usuario
        from gos.version import APP_VERSION, APP_VERSION_LABEL

        modules = []
        with app.app_context():
            from gos.modulos.hwo import module_descriptor as hwo_descriptor
            from gos.modulos.objetivos import module_descriptor as objetivos_descriptor
            from gos.modulos.vacaciones import module_descriptor as vacaciones_descriptor
            from gos.modulos.capacitacion import module_descriptor as capacitacion_descriptor

            modules.append(objetivos_descriptor())
            modules.append(capacitacion_descriptor())
            modules.append(hwo_descriptor())
            modules.append(vacaciones_descriptor())

        modules = modulos_para_usuario(current_user, modules)

        current_module = ""
        if request.path.startswith("/gos/objetivos"):
            current_module = "objetivos"
        elif request.path.startswith("/gos/hwo"):
            current_module = "hwo"
        elif request.path.startswith("/gos/vacaciones"):
            current_module = "vacaciones"
        elif request.path.startswith("/gos/capacitacion"):
            current_module = "capacitacion"

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
    from gos.blueprints.usuarios import bp as usuarios_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(usuarios_bp, url_prefix="/usuarios")


def _register_modules(app: Flask) -> None:
    from gos.modulos.hwo import register as register_hwo
    from gos.modulos.objetivos import register as register_objetivos
    from gos.modulos.vacaciones import register as register_vacaciones
    from gos.modulos.capacitacion import register as register_capacitacion

    register_objetivos(app)
    register_capacitacion(app)
    register_hwo(app)
    register_vacaciones(app)


def _register_auto_login(app: Flask) -> None:
    if not app.config.get("AUTO_LOGIN"):
        return

    from flask import request
    from flask_login import current_user, login_user

    from gos.services import auth_service

    @app.before_request
    def _auto_login():
        if request.endpoint in (
            "static",
            "objetivos_static.static",
            "capacitacion_static.static",
            "hwo_static.static",
            "vacaciones_static.static",
        ):
            return
        if current_user.is_authenticated:
            return
        user = auth_service.obtener_o_crear_usuario_default()
        login_user(user, remember=True)
