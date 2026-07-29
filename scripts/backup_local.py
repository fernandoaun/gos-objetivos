"""Respaldo local de bases y datos de instance/ (no van a git).

Uso:
  python scripts/backup_local.py              # backup diario (retiene N días)
  python scripts/backup_local.py --snapshot pre-gitahead
  python scripts/backup_local.py --keep 30

Destino: instance/backups/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUP_ROOT = ROOT / "instance" / "backups"
DEFAULT_KEEP_DAYS = 14

# Archivos/carpetas a respaldar (relativos a instance/)
SOURCES = (
    "gos.db",
    "gos-DELL_FERAUN.db",
    "gos_objetivos.db",
    "vacaciones/indicadores.db",
    "hwo/datasets.json",
    "hwo/modalidad.json",
)


def _git_info() -> dict[str, str]:
    info = {"commit": "?", "branch": "?", "status": "?"}
    try:
        info["commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        info["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        info["status"] = "dirty" if dirty else "clean"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass
    return info


def _safe_copy_sqlite(src: Path, dest: Path) -> None:
    """Copia consistente aunque la app tenga la DB abierta."""
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


def _copy_file(src: Path, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".db":
        _safe_copy_sqlite(src, dest)
    else:
        shutil.copy2(src, dest)
    return dest.stat().st_size


def _prune_daily(keep_days: int) -> list[Path]:
    """Borra carpetas diario-YYYYMMDD más viejas que keep_days. No toca snapshots."""
    if keep_days <= 0 or not BACKUP_ROOT.is_dir():
        return []
    removed: list[Path] = []
    today = datetime.now().date()
    for path in sorted(BACKUP_ROOT.iterdir()):
        if not path.is_dir() or not path.name.startswith("diario-"):
            continue
        stamp = path.name.removeprefix("diario-")
        try:
            day = datetime.strptime(stamp, "%Y%m%d").date()
        except ValueError:
            continue
        age = (today - day).days
        if age > keep_days:
            shutil.rmtree(path, ignore_errors=True)
            removed.append(path)
    return removed


def run_backup(*, snapshot: str | None, keep_days: int) -> Path:
    now = datetime.now()
    if snapshot:
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in snapshot.strip())
        safe = safe.strip("-_") or "snapshot"
        folder_name = f"snapshot-{safe}-{now.strftime('%Y%m%d-%H%M%S')}"
    else:
        folder_name = f"diario-{now.strftime('%Y%m%d')}"

    dest_dir = BACKUP_ROOT / folder_name
    # Si ya hubo un diario hoy, sumamos hora para no pisarlo
    if not snapshot and dest_dir.exists():
        dest_dir = BACKUP_ROOT / f"diario-{now.strftime('%Y%m%d-%H%M%S')}"

    dest_dir.mkdir(parents=True, exist_ok=True)
    instance = ROOT / "instance"
    copied: list[dict] = []
    missing: list[str] = []

    for rel in SOURCES:
        src = instance / rel
        if not src.is_file():
            missing.append(rel)
            continue
        size = _copy_file(src, dest_dir / rel)
        copied.append({"path": rel, "bytes": size})

    git = _git_info()
    manifest = {
        "created_at": now.isoformat(timespec="seconds"),
        "type": "snapshot" if snapshot else "diario",
        "label": snapshot or folder_name,
        "project_root": str(ROOT),
        "git": git,
        "files": copied,
        "missing": missing,
    }
    (dest_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"GOS backup — {manifest['created_at']}",
        f"Tipo: {manifest['type']}",
        f"Git: {git['branch']} @ {git['commit']} ({git['status']})",
        "",
        "Archivos:",
    ]
    for item in copied:
        kb = item["bytes"] // 1024
        lines.append(f"  {item['path']} ({kb} KB)")
    if missing:
        lines.append("")
        lines.append("No encontrados (ok si no existen):")
        for m in missing:
            lines.append(f"  - {m}")
    (dest_dir / "LEEME.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    pruned = [] if snapshot else _prune_daily(keep_days)
    print(f"Backup OK: {dest_dir}")
    print(f"  Git: {git['branch']} @ {git['commit']} ({git['status']})")
    print(f"  Archivos: {len(copied)}")
    if pruned:
        print(f"  Eliminados (>{keep_days} días): {len(pruned)}")
    return dest_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup local de GOS Objetivos")
    parser.add_argument(
        "--snapshot",
        metavar="NOMBRE",
        help="Backup nombrado (no se borra con la retención diaria)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP_DAYS,
        help=f"Días de backups diarios a conservar (default {DEFAULT_KEEP_DAYS})",
    )
    args = parser.parse_args()
    try:
        run_backup(snapshot=args.snapshot, keep_days=args.keep)
    except Exception as exc:  # noqa: BLE001 — script CLI
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
