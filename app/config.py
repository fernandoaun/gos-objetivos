import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url and ".render.com" in url and "sslmode=" not in url:
        url += "&sslmode=require" if "?" in url else "?sslmode=require"
    if url:
        return url
    return f"sqlite:///{BASE_DIR / 'instance' / 'gos_objetivos.db'}"


def _engine_options() -> dict:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgres"):
        return {"pool_pre_ping": True}
    return {}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options()
    INSTANCE_PATH = BASE_DIR / "instance"


class DevelopmentConfig(Config):
    DEBUG = True
    AUTO_LOGIN = os.environ.get("GOS_AUTO_LOGIN", "true").lower() in ("1", "true", "yes")


class ProductionConfig(Config):
    DEBUG = False
    AUTO_LOGIN = False


class TestingConfig(Config):
    TESTING = True
    AUTO_LOGIN = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
