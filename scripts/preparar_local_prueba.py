"""Prepara (o refresca) una base local de prueba aislada de Render.

Copia instance/gos.db (y datos auxiliares) a instance/prueba/.
No lee ni escribe la base de Render.

Uso:
  python scripts/preparar_local_prueba.py
  python scripts/preparar_local_prueba.py --desde-snapshot
  python scripts/preparar_local_prueba.py --reset
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTANCE = ROOT / "instance"
PRUEBA = INSTANCE / "prueba"
BACKUP_ROOT = INSTANCE / "backups"

MAIN_FILES = (
    "gos.db",
    "gos-DELL_FERAUN.db",
    "gos_objetivos.db",
)
EXTRA_FILES = (
    "vacaciones/indicadores.db",
    "hwo/datasets.json",
    "hwo/modalidad.json",
)


def _safe_copy_sqlite(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        src_conn = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
        try:
            dest_conn = sqlite3.connect(dest.as_posix())
            try:
                src_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            src_conn.close()
    except sqlite3.Error:
        shutil.copy2(src, dest)


def _copy_one(src: Path, dest: Path) -> bool:
    if not src.is_file():
        return False
    if src.suffix.lower() == ".db":
        _safe_copy_sqlite(src, dest)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return True


def _latest_snapshot() -> Path | None:
    if not BACKUP_ROOT.is_dir():
        return None
    snaps = sorted(
        (
            p
            for p in BACKUP_ROOT.iterdir()
            if p.is_dir() and p.name.startswith("snapshot-")
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return snaps[0] if snaps else None


def _source_root(*, desde_snapshot: bool) -> Path:
    if desde_snapshot:
        snap = _latest_snapshot()
        if not snap:
            print("ERROR: no hay snapshot en instance/backups/", file=sys.stderr)
            sys.exit(1)
        return snap
    return INSTANCE


def prepare(*, desde_snapshot: bool, reset: bool) -> Path:
    src_root = _source_root(desde_snapshot=desde_snapshot)
    PRUEBA.mkdir(parents=True, exist_ok=True)

    dest_main = PRUEBA / "gos.db"
    if dest_main.is_file() and not reset and not desde_snapshot:
        print(f"Ya existe base de prueba: {dest_main}")
        print("Usá --reset para recopiar desde la base de hoy.")
        print("Usá --desde-snapshot --reset para volver al último snapshot.")
        return PRUEBA

    copied = 0
    for name in MAIN_FILES + EXTRA_FILES:
        src = src_root / name
        # snapshot guarda gos.db en la raíz del snapshot
        if not src.is_file() and src_root == INSTANCE:
            continue
        if _copy_one(src, PRUEBA / name):
            copied += 1
            print(f"  OK {name}")

    if not (PRUEBA / "gos.db").is_file():
        # fallback: priorizar gos.db de instance
        fallback = INSTANCE / "gos.db"
        if fallback.is_file():
            _copy_one(fallback, PRUEBA / "gos.db")
            copied += 1
            print("  OK gos.db (desde instance/)")
        else:
            print("ERROR: no se encontró gos.db para copiar", file=sys.stderr)
            sys.exit(1)

    meta = PRUEBA / "ORIGEN.txt"
    meta.write_text(
        "\n".join(
            [
                f"Creado: {datetime.now().isoformat(timespec='seconds')}",
                f"Origen: {src_root}",
                f"Archivos copiados: {copied}",
                "",
                "Esta carpeta es SOLO local.",
                "Abrir con: ABRIR LOCAL PRUEBA.bat",
                "NO subir a Render mientras pruebes (no uses SUBIR BACKUP A RENDER.bat).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Base de prueba lista: {PRUEBA}")
    return PRUEBA


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--desde-snapshot",
        action="store_true",
        help="Copiar desde el último snapshot-* (no desde gos.db vivo)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Pisa la base de prueba con una copia fresca",
    )
    args = parser.parse_args()
    prepare(desde_snapshot=args.desde_snapshot, reset=args.reset)


if __name__ == "__main__":
    main()
