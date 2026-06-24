"""Asegura el usuario admin. Uso en Render: python scripts/ensure_admin.py"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gos.services.bootstrap_service import ensure_initial_admin
from wsgi import app


def main() -> None:
    email = os.environ.get("GOS_ADMIN_EMAIL", "admin@demo.local").strip().lower()
    password = os.environ.get("GOS_ADMIN_PASSWORD", "admin123")

    with app.app_context():
        ensure_initial_admin()
        from gos.models import Usuario

        user = Usuario.query.filter_by(email=email).first()
        if user and user.check_password(password):
            print(f"OK — login: {email}")
        else:
            print(f"ERROR — no se pudo verificar {email}")
            sys.exit(1)


if __name__ == "__main__":
    main()
