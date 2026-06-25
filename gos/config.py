from pathlib import Path

from gos import env

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INSTANCE_PATH = BASE_DIR / "instance"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def apply_env_to_app(app) -> None:
    """Aplica variables de entorno después de load_dotenv()."""
    app.config["SECRET_KEY"] = env.secret_key()
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///:memory:" if app.config.get("TESTING") else env.sqlalchemy_database_uri()
    )
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = env.sqlalchemy_engine_options()
    app.config["AUTO_LOGIN"] = env.auto_login_enabled()
    app.config["SHOW_LOGIN_DEMO_HINT"] = env.is_development() and not env.is_production()
    app.config["GOS_ADMIN_EMAIL"] = env.admin_email()

    if env.is_production():
        env.validate_production()
