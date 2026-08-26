"""Sube instance/capacitacion/gos_cap.db al Postgres de Cap en Render.

Usa la URL externa de la DB Cap (Dashboard → gos-capacitacion-db → External).

  set RENDER_CAP_DATABASE_URL=postgresql://...
  set GOS_IMPORT_SECRET=...   # no obligatorio aquí (import directo)
  python scripts/subir_cap_a_render.py
  python scripts/subir_cap_a_render.py --yes
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from gos import env


def main() -> int:
    auto_yes = "--yes" in sys.argv or "-y" in sys.argv
    local = Path(
        os.environ.get("GOS_CAP_LOCAL_DB")
        or ""
    )
    if not str(local):
        preferred = ROOT / "instance" / "capacitacion" / "gos_cap.db.tmp"
        fallback = ROOT / "instance" / "capacitacion" / "gos_cap.db"
        local = preferred if preferred.is_file() else fallback
    target = (
        os.environ.get("RENDER_CAP_DATABASE_URL")
        or os.environ.get("RENDER_DATABASE_URL")
        or ""
    ).strip()

    if not local.is_file():
        print(f"ERROR: no existe {local}")
        print("Ejecutá antes SEPARAR CAPACITACION.bat")
        return 1
    if not target.startswith(("postgres://", "postgresql://")):
        print("ERROR: definí RENDER_CAP_DATABASE_URL (URL externa Postgres Cap en Render).")
        return 1

    print(f"Local:  {local}")
    print(f"Target: {target.split('@')[-1] if '@' in target else '(postgres)'}")
    if not auto_yes:
        ok = input("Subir Capacitación a Render Cap? Escribí SI: ").strip()
        if ok != "SI":
            print("Cancelado.")
            return 1

    try:
        import psycopg2  # noqa: F401
    except ModuleNotFoundError:
        print("ERROR: pip install psycopg2-binary")
        return 1

    from gos.modulos.objetivos.services.import_service import importar_sqlite

    counts = importar_sqlite(local, target, allow_cap_overwrite=True)
    cap = {k: v for k, v in counts.items() if k.startswith("cap_") and v}
    print("OK Cap:", cap or counts)
    print("Abrí el servicio gos-capacitacion en Render y verificá login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
