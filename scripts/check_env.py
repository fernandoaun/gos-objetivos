"""Valida variables de entorno. Uso: python scripts/check_env.py [--production]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from gos import env


def _print_report(report: env.EnvAudit) -> None:
    print(f"Entorno: {report.env_name}")
    print("-" * 50)
    for line in report.ok:
        print(f"  OK   {line}")
    for line in report.warnings:
        print(f"  AVISO {line}")
    for line in report.errors:
        print(f"  ERROR {line}")
    print("-" * 50)
    if report.passed:
        print("Resultado: OK")
    else:
        print("Resultado: FALLÓ — corregí los errores antes de deployar.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validar .env de GOS")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Validar como producción (aunque FLASK_ENV sea development)",
    )
    args = parser.parse_args()
    target = "production" if args.production else None
    report = env.audit_env(target)
    _print_report(report)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
