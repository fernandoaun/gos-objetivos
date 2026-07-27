"""Sube un backup SQLite local a Render para importar en la base del servicio web.

Antes de subir:
- Copia de seguridad local en instance/backups/
- Muestra conteos y pide confirmación (salvo --yes)
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import urllib.error
import urllib.request
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv()

from gos import env
from gos.modulos.objetivos.services.import_service import PROTECTED_TABLES, TABLES

API_PATH = "/gos/objetivos/api/v1/admin/import-db"
BACKUP_DIR = ROOT / "instance" / "backups"


def _local_counts(db_path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        names = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in TABLES:
            if table in names:
                counts[table] = conn.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]
    finally:
        conn.close()
    return counts


def _make_local_backup(db_path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"gos-pre-upload-{stamp}.db"
    shutil.copy2(db_path, dest)
    return dest


def main() -> None:
    auto_yes = "--yes" in sys.argv or "-y" in sys.argv
    secret = env.import_secret()
    base_url = env.render_service_url().rstrip("/")
    local_db = env.local_backup_db_path()

    if not secret:
        print("ERROR: definí GOS_IMPORT_SECRET en .env o en Render → Environment.")
        sys.exit(1)
    if not local_db.is_file():
        print(f"ERROR: no existe {local_db}")
        print("Tip: definí GOS_LOCAL_DB_PATH si el backup está en otra ruta.")
        sys.exit(1)

    counts = _local_counts(local_db)
    empty_protected = sorted(
        t for t in PROTECTED_TABLES if counts.get(t, 0) == 0 and t in TABLES
    )
    nonempty = {k: v for k, v in counts.items() if v}

    print(f"Origen: {local_db} ({local_db.stat().st_size // 1024} KB)")
    print(f"Destino: {base_url}{API_PATH}")
    print("Tablas con datos en el SQLite local:")
    for table, n in sorted(nonempty.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {table}: {n}")
    if empty_protected:
        print()
        print(
            "AVISO: tablas protegidas VACÍAS o menores en local."
            " Si Render tiene MÁS filas, se CONSERVAN (no se borran):"
        )
        for table in empty_protected:
            print(f"  - {table}")

    backup = _make_local_backup(local_db)
    print()
    print(f"Backup local creado: {backup}")

    if not auto_yes:
        print()
        ans = input("¿Subir a Render? Escribí SI para continuar: ").strip()
        if ans.upper() != "SI":
            print("Cancelado. El backup local se conservó.")
            sys.exit(0)

    boundary = "----GOSBoundary7MA4YWxkTrZu0gW"
    db_bytes = local_db.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="database"; filename="{local_db.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + db_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}{API_PATH}",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Import-Secret": secret,
        },
    )

    print(f"Subiendo {local_db.name} ({len(db_bytes) // 1024} KB) a {base_url} ...")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            print(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"ERROR de conexión: {exc.reason}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
