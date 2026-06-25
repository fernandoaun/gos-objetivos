"""
Variables de entorno — única fuente de verdad para configuración sensible.

Uso: importar getters desde aquí; no leer os.environ disperso en el código.
Copiá .env.example a .env en desarrollo local (nunca commitear .env).
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

_runtime_env: str | None = None

_DEV_SECRET_PLACEHOLDERS = frozenset({
    "",
    "dev-secret-change-me",
    "change-me-in-production",
    "change-me",
})


def _get(name: str, default: str | None = None) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return default
    stripped = raw.strip()
    return stripped if stripped else default


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in ("1", "true", "yes")


def set_runtime_env(name: str | None) -> None:
    """Fija el entorno activo (create_app / tests)."""
    global _runtime_env
    _runtime_env = name


def flask_env() -> str:
    if _runtime_env:
        return _runtime_env
    return _get("FLASK_ENV", "development") or "development"


def is_production() -> bool:
    return flask_env() == "production"


def is_testing() -> bool:
    return flask_env() == "testing"


def is_development() -> bool:
    return flask_env() == "development"


# ── Seguridad ─────────────────────────────────────────────────────────────


def secret_key() -> str:
    if is_production():
        key = _get("SECRET_KEY")
        if not key or key in _DEV_SECRET_PLACEHOLDERS:
            raise RuntimeError(
                "SECRET_KEY debe definirse en producción (Render → Environment o .env)."
            )
        return key
    return _get("SECRET_KEY", "dev-secret-change-me") or "dev-secret-change-me"


def import_secret() -> str | None:
    return _get("GOS_IMPORT_SECRET")


def import_auth_ok(provided: str) -> bool:
    expected = import_secret()
    return bool(expected and provided and provided == expected)


def admin_email() -> str:
    return (_get("GOS_ADMIN_EMAIL", "admin@demo.local") or "admin@demo.local").lower()


def admin_password() -> str:
    if is_production():
        pwd = _get("GOS_ADMIN_PASSWORD")
        if not pwd:
            raise RuntimeError(
                "GOS_ADMIN_PASSWORD debe definirse en producción."
            )
        if len(pwd) < 8:
            raise RuntimeError(
                "GOS_ADMIN_PASSWORD debe tener al menos 8 caracteres en producción."
            )
        return pwd
    return _get("GOS_ADMIN_PASSWORD", "admin123") or "admin123"


def admin_nombre() -> str:
    return _get("GOS_ADMIN_NOMBRE", "Administrador") or "Administrador"


def empresa_nombre() -> str:
    return _get("GOS_EMPRESA_NOMBRE", "Empresa Demo S.A.") or "Empresa Demo S.A."


def auto_login_enabled() -> bool:
    if is_production() or is_testing():
        return False
    return _bool("GOS_AUTO_LOGIN", True)


def dev_login_email() -> str:
    return (_get("GOS_DEV_LOGIN_EMAIL", "admin@gos.local") or "admin@gos.local").lower()


def dev_login_password() -> str:
    return _get("GOS_DEV_LOGIN_PASSWORD", "gos") or "gos"


def dev_login_nombre() -> str:
    return _get("GOS_DEV_LOGIN_NOMBRE", "Usuario GOS") or "Usuario GOS"


def dev_empresa_nombre() -> str:
    return _get("GOS_DEV_EMPRESA_NOMBRE", "GOS") or "GOS"


# ── Base de datos ───────────────────────────────────────────────────────


def database_url() -> str | None:
    url = _get("DATABASE_URL")
    if not url:
        return None
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if ".render.com" in url and "sslmode=" not in url:
        url += "&sslmode=require" if "?" in url else "?sslmode=require"
    return url


def sqlite_database_url() -> str:
    custom = _get("GOS_DATABASE_PATH")
    if custom:
        return f"sqlite:///{Path(custom).resolve()}"
    return f"sqlite:///{BASE_DIR / 'instance' / 'gos.db'}"


def sqlalchemy_database_uri() -> str:
    return database_url() or sqlite_database_url()


def sqlalchemy_engine_options() -> dict:
    url = _get("DATABASE_URL", "") or ""
    if url.startswith("postgres"):
        return {"pool_pre_ping": True}
    return {}


# ── Rutas de datos (módulos) ────────────────────────────────────────────


def hwo_data_dir() -> Path:
    custom = _get("GOS_HWO_DATA_DIR")
    if custom:
        return Path(custom).resolve()
    return BASE_DIR / "instance" / "hwo"


def vacaciones_db_path() -> Path:
    custom = _get("GOS_VACACIONES_DB_PATH")
    if custom:
        return Path(custom).resolve()
    return BASE_DIR / "instance" / "vacaciones" / "indicadores.db"


def kpi_excel_path() -> Path | None:
    custom = _get("GOS_KPI_EXCEL_PATH")
    if custom:
        return Path(custom)
    return None


def render_database_url() -> str | None:
    """URL externa de PostgreSQL en Render (scripts de importación directa)."""
    return _get("RENDER_DATABASE_URL") or database_url()


def local_backup_db_path() -> Path:
    custom = _get("GOS_LOCAL_DB_PATH")
    if custom:
        return Path(custom)
    instance = BASE_DIR / "instance"
    for name in ("gos.db", "gos_objetivos.db"):
        candidate = instance / name
        if candidate.is_file():
            return candidate
    return instance / "gos.db"


def render_service_url() -> str:
    return _get("GOS_RENDER_URL", "https://gos-objetivos.onrender.com") or "https://gos-objetivos.onrender.com"


# ── Correo (notificaciones) ───────────────────────────────────────────────


def smtp_host() -> str | None:
    return _get("GOS_SMTP_HOST")


def smtp_port() -> int:
    raw = _get("GOS_SMTP_PORT", "587")
    try:
        return int(raw or "587")
    except ValueError:
        return 587


def smtp_user() -> str | None:
    return _get("GOS_SMTP_USER")


def smtp_password() -> str | None:
    return _get("GOS_SMTP_PASSWORD")


def smtp_from() -> str:
    return _get("GOS_SMTP_FROM", "noreply@gos.local") or "noreply@gos.local"


def smtp_tls() -> bool:
    return _bool("GOS_SMTP_TLS", True)


# ── IA (futuro) ─────────────────────────────────────────────────────────


def openai_api_key() -> str | None:
    return _get("OPENAI_API_KEY")


def openai_model() -> str:
    return _get("OPENAI_MODEL", "gpt-4o-mini") or "gpt-4o-mini"


# ── Validación al arranque ────────────────────────────────────────────────


def validate_production() -> None:
    """Falla rápido si producción no tiene secretos mínimos."""
    if not is_production():
        return
    secret_key()
    admin_password()


# ── Auditoría (scripts/check_env.py) ──────────────────────────────────────


class EnvAudit:
    __slots__ = ("env_name", "errors", "warnings", "ok")

    def __init__(self, env_name: str) -> None:
        self.env_name = env_name
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.ok: list[str] = []

    @property
    def passed(self) -> bool:
        return not self.errors


def audit_env(env_name: str | None = None) -> EnvAudit:
    """Revisa variables sin levantar la app. No modifica _runtime_env."""
    name = env_name or _get("FLASK_ENV", "development") or "development"
    report = EnvAudit(name)
    is_prod = name == "production"
    is_dev = name == "development"

    if not Path(BASE_DIR / ".env").is_file() and is_dev:
        report.warnings.append("No existe .env — ejecutá: python scripts/setup_env.py")

    sk = _get("SECRET_KEY")
    if is_prod:
        if not sk or sk in _DEV_SECRET_PLACEHOLDERS:
            report.errors.append("SECRET_KEY: obligatorio en producción (valor aleatorio fuerte).")
        else:
            report.ok.append("SECRET_KEY configurado.")
    elif sk and sk not in _DEV_SECRET_PLACEHOLDERS:
        report.ok.append("SECRET_KEY personalizado (desarrollo).")

    pwd = _get("GOS_ADMIN_PASSWORD")
    if is_prod:
        if not pwd:
            report.errors.append("GOS_ADMIN_PASSWORD: obligatorio en producción (mín. 8 caracteres).")
        elif len(pwd) < 8:
            report.errors.append("GOS_ADMIN_PASSWORD: debe tener al menos 8 caracteres.")
        else:
            report.ok.append("GOS_ADMIN_PASSWORD configurado.")
    elif pwd:
        report.ok.append("GOS_ADMIN_PASSWORD definido (desarrollo).")

    imp = _get("GOS_IMPORT_SECRET")
    if is_prod and not imp:
        report.warnings.append(
            "GOS_IMPORT_SECRET: no definido — la API de importación de backup estará deshabilitada."
        )
    elif imp:
        report.ok.append("GOS_IMPORT_SECRET configurado.")

    db = database_url()
    if is_prod:
        if not db or not db.startswith("postgres"):
            report.errors.append("DATABASE_URL: producción requiere PostgreSQL.")
        else:
            report.ok.append("DATABASE_URL (PostgreSQL).")
    elif db:
        report.ok.append(f"DATABASE_URL ({'PostgreSQL' if db.startswith('postgres') else 'custom'}).")
    else:
        local = BASE_DIR / "instance" / "gos.db"
        report.ok.append(f"Base SQLite local: {local}")

    if _bool("GOS_AUTO_LOGIN", False) and is_prod:
        report.errors.append("GOS_AUTO_LOGIN no puede estar activo en producción.")

    if is_dev and _bool("GOS_AUTO_LOGIN", True):
        report.ok.append("GOS_AUTO_LOGIN activo (solo desarrollo).")

    excel = kpi_excel_path()
    if excel is None:
        report.warnings.append(
            "GOS_KPI_EXCEL_PATH: no definido — importación de KPI desde Excel deshabilitada."
        )
    elif not excel.is_file():
        report.warnings.append(f"GOS_KPI_EXCEL_PATH: archivo no encontrado ({excel}).")
    else:
        report.ok.append("GOS_KPI_EXCEL_PATH accesible.")

    if not hwo_data_dir().parent.exists():
        report.warnings.append("instance/ no existe — se creará al primer uso.")

    return report
