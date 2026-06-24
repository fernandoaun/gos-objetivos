"""
Copia todos los datos del SQLite local a PostgreSQL (Render).

Recomendado: scripts/subir_backup_a_render.py (usa la misma base que la web).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOCAL_DB = ROOT / "instance" / "gos_objetivos.db"


def main() -> None:
    target_url = os.environ.get("RENDER_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not target_url or not target_url.startswith(("postgres://", "postgresql://")):
        print("ERROR: definí RENDER_DATABASE_URL con la URL externa de PostgreSQL en Render.")
        print("Mejor usá: SUBIR BACKUP A RENDER.bat (más confiable).")
        sys.exit(1)
    if "..." in target_url or "tu URL" in target_url.lower():
        print("ERROR: pegaste el texto de ejemplo, no la URL real de Render.")
        sys.exit(1)
    try:
        import psycopg2  # noqa: F401
    except ModuleNotFoundError:
        print("ERROR: falta psycopg2. Ejecutá: python -m pip install psycopg2-binary")
        sys.exit(1)

    from app.services.import_service import importar_sqlite_or_exit

    importar_sqlite_or_exit(LOCAL_DB, target_url)


if __name__ == "__main__":
    main()
