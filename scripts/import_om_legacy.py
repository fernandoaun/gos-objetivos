"""Importa módulos O&M desde un JSON legacy (idempotente por code).

Uso:
  python scripts/import_om_legacy.py
  python scripts/import_om_legacy.py --file ruta/al/export.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "gos" / "modulos" / "om" / "data" / "modulos_data.legacy.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Importar módulos O&M desde JSON")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_FILE,
        help=f"Ruta al JSON (default: {DEFAULT_FILE})",
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"No se encontró {args.file}", file=sys.stderr)
        return 1

    modules = json.loads(args.file.read_text(encoding="utf-8"))
    if not isinstance(modules, list):
        print("El archivo no contiene un array de módulos.", file=sys.stderr)
        return 1

    sys.path.insert(0, str(ROOT))
    from gos import create_app
    from gos.modulos.om import services
    from gos.modulos.om.models import OmModule
    from gos.extensions import db
    from sqlalchemy import select, func

    app = create_app()
    with app.app_context():
        before = db.session.scalar(
            select(func.count())
            .select_from(OmModule)
            .where(OmModule.deleted_at.is_(None))
        ) or 0
        print(f"Módulos en la base antes: {before}")
        print(f"Módulos a procesar: {len(modules)}")
        result = services.import_modules_payload(modules, user_id=None)
        after = db.session.scalar(
            select(func.count())
            .select_from(OmModule)
            .where(OmModule.deleted_at.is_(None))
        ) or 0

    print("--- Resumen ---")
    print(f"Creados: {result['created']}")
    print(f"Omitidos (código ya existente): {result['skipped']}")
    print(f"Errores: {len(result['errors'])}")
    for err in result["errors"]:
        print(f"  - {err.get('code')}: {err.get('message')}")
    print(f"Módulos en la base después: {after} (antes: {before})")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
