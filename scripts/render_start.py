"""Inicializa tablas antes de Gunicorn (Render). No aborta el deploy si falla."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
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
