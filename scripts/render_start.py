"""Inicializa tablas antes de Gunicorn (Render)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")

    from gos import env

    report = env.audit_env("production")
    if not report.passed:
        for err in report.errors:
            print(f"[render_start] ERROR env: {err}", file=sys.stderr)
        print(
            "\n[render_start] Configurá en Render → tu servicio → Environment:\n"
            "  GOS_ADMIN_PASSWORD  contraseña de admin (mín. 8 caracteres)\n"
            "  SECRET_KEY          clave aleatoria (si falta)\n"
            "  GOS_IMPORT_SECRET   clave para importar backups (recomendado)\n"
            "Luego: Save Changes (Render redeploya solo).\n"
            "Login: admin@demo.local + la contraseña que definiste.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from gos import create_app
        from gos.extensions import db
        from gos.services.bootstrap_service import ensure_initial_admin
        from gos.modulos.objetivos import ensure_planeamiento_config

        app = create_app("production")
        with app.app_context():
            db.create_all()
            ensure_initial_admin()
            ensure_planeamiento_config()
            uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            backend = "postgresql" if uri.startswith("postgres") else "sqlite"
            print(f"[render_start] Base OK ({backend})")
    except Exception as exc:
        print(f"[render_start] AVISO: init DB falló: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
