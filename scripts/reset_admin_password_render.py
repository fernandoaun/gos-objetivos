"""
Resetea la contraseña de un usuario admin en PostgreSQL de Render.

Uso (PowerShell):
  $env:RENDER_DATABASE_URL = "postgresql://..."
  python scripts/reset_admin_password_render.py --password "TuNuevaClave"

Opcional:
  --email admin@demo.local
  --list   (solo lista usuarios, no cambia nada)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv()


def _target_url() -> str:
    url = (
        os.environ.get("RENDER_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip().strip('"').strip("'")
    if not url.startswith(("postgres://", "postgresql://")):
        print(
            "ERROR: definí RENDER_DATABASE_URL con la External Database URL de Render."
        )
        sys.exit(1)
    if "..." in url or "tu URL" in url.lower():
        print("ERROR: pegaste un texto de ejemplo, no la URL real.")
        sys.exit(1)
    # SQLAlchemy / psycopg2 suelen preferir postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    # El "+" en la clave de Render debe ir como %2B
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        creds, hostpart = rest.rsplit("@", 1)
        if ":" in creds:
            user, password = creds.split(":", 1)
            password = password.replace("+", "%2B")
            url = f"{scheme}://{user}:{password}@{hostpart}"
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset admin password on Render")
    parser.add_argument(
        "--email",
        default="admin@gos.local,admin@demo.local",
        help="Uno o varios emails separados por coma",
    )
    parser.add_argument("--password", default="")
    parser.add_argument("--list", action="store_true", help="Listar usuarios y salir")
    args = parser.parse_args()

    os.environ["DATABASE_URL"] = _target_url()
    os.environ["FLASK_ENV"] = "production"
    # Evitar que falte GOS_ADMIN_PASSWORD al importar env en production
    os.environ.setdefault("GOS_ADMIN_PASSWORD", "temporary-reset-placeholder-8")

    print("Conectando a Render (puede tardar unos segundos)...")
    from wsgi import app
    from gos.extensions import db
    from gos.models import Usuario

    with app.app_context():
        users = Usuario.query.order_by(Usuario.id).all()
        if not users:
            print("No hay usuarios en la base de Render.")
            sys.exit(1)

        print("Usuarios en Render:")
        for u in users:
            estado = "activo" if u.activo else "inactivo"
            print(f"  - {u.email}  ({u.rol}, {estado})")

        if args.list:
            return

        password = args.password.strip()
        if len(password) < 8:
            print("ERROR: --password debe tener al menos 8 caracteres.")
            sys.exit(1)

        emails = [e.strip().lower() for e in args.email.split(",") if e.strip()]
        from werkzeug.security import generate_password_hash

        ok = 0
        for email in emails:
            user = Usuario.query.filter_by(email=email).first()
            if not user:
                print(f"AVISO: no existe {email} en Render.")
                continue

            # pbkdf2: compatible entre Python local y Render
            user.password_hash = generate_password_hash(
                password, method="pbkdf2:sha256"
            )
            user.activo = True
            if user.rol not in ("administrador", "admin"):
                user.rol = "administrador"
            db.session.commit()
            db.session.refresh(user)
            if not user.check_password(password):
                print(f"ERROR — check_password falló para {email}")
                sys.exit(1)
            print(f"OK — contraseña actualizada y verificada para {email}")
            ok += 1

        if not ok:
            print("ERROR: no se actualizó ningún usuario.")
            sys.exit(1)

        print("Entrá en https://gos-objetivos.onrender.com/auth/login")
        print(f"  Email: {emails[0]}")
        print(f"  Contraseña: {password}")
        print("Tip: ventana privada del navegador (sin autocompletar viejo).")


if __name__ == "__main__":
    main()
