"""Crea .env desde .env.example con secretos generados. Uso: python scripts/setup_env.py [--force]"""
from __future__ import annotations

import argparse
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / ".env.example"
TARGET = ROOT / ".env"


def _generate_secrets(content: str) -> str:
    secret_key = secrets.token_hex(32)
    import_secret = secrets.token_hex(24)

    replacements = {
        r"^SECRET_KEY=.*$": f"SECRET_KEY={secret_key}",
        r"^GOS_IMPORT_SECRET=.*$": f"GOS_IMPORT_SECRET={import_secret}",
    }
    lines = content.splitlines()
    out: list[str] = []
    replaced = set()
    for line in lines:
        updated = line
        for pattern, value in replacements.items():
            if re.match(pattern, line):
                updated = value
                replaced.add(pattern)
                break
        out.append(updated)
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generar .env local para GOS")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribir .env existente",
    )
    args = parser.parse_args()

    if not EXAMPLE.is_file():
        print(f"ERROR: falta {EXAMPLE}")
        return 1

    if TARGET.is_file() and not args.force:
        print(f".env ya existe ({TARGET})")
        print("Usá --force para regenerar secretos.")
        return 0

    content = EXAMPLE.read_text(encoding="utf-8")
    TARGET.write_text(_generate_secrets(content), encoding="utf-8")
    print(f"Listo: {TARGET}")
    print("  SECRET_KEY y GOS_IMPORT_SECRET generados automáticamente.")
    print("  Desarrollo: GOS_AUTO_LOGIN=true (entrada sin login).")
    print("  Login manual: admin@demo.local / admin123 (GOS_ADMIN_PASSWORD en .env)")
    print()
    print("Validar: python scripts/check_env.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
