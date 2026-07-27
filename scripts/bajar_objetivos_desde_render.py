"""Baja tablas de Objetivos/FODA desde Render e las importa en el SQLite local."""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv()

from gos import env

API_PATH = "/gos/objetivos/api/v1/admin/export-tables"
DEFAULT_TABLES = [
    "planeamiento_config",
    "sectores",
    "areas",
    "responsables",
    "objetivos",
    "kpi_indicadores",
    "foda_documentos",
    "foda_items",
    "dafo_tareas",
]
BACKUP_DIR = ROOT / "instance" / "backups"


def _fetch(tables: list[str]) -> dict:
    secret = env.import_secret()
    base = env.render_service_url().rstrip("/")
    if not secret:
        raise SystemExit("ERROR: definí GOS_IMPORT_SECRET en .env")
    body = json.dumps({"tables": tables}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}{API_PATH}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Import-Secret": secret,
        },
    )
    print(f"Descargando desde {base}{API_PATH} ...")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"
        ) from exc


def _backup_local(db_path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"gos-pre-pull-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    shutil.copy2(db_path, dest)
    return dest


def _apply_to_sqlite(db_path: Path, tables_data: dict[str, list]) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    applied: dict[str, int] = {}
    try:
        existing = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        conn.execute("PRAGMA foreign_keys = OFF")
        for table, rows in tables_data.items():
            if table not in existing:
                print(f"  skip {table}: no existe en local")
                continue
            cols_info = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
            physical = {c[1] for c in cols_info}
            conn.execute(f'DELETE FROM "{table}"')
            if not rows:
                applied[table] = 0
                continue
            for row in rows:
                filtered = {k: v for k, v in row.items() if k in physical}
                if not filtered:
                    continue
                # JSON columns may arrive as list/dict
                for k, v in list(filtered.items()):
                    if isinstance(v, (dict, list)):
                        filtered[k] = json.dumps(v, ensure_ascii=False)
                cols = list(filtered.keys())
                placeholders = ",".join("?" for _ in cols)
                col_sql = ",".join(f'"{c}"' for c in cols)
                conn.execute(
                    f'INSERT INTO "{table}" ({col_sql}) VALUES ({placeholders})',
                    [filtered[c] for c in cols],
                )
            applied[table] = len(rows)
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()
    return applied


def main() -> None:
    local_db = env.local_backup_db_path()
    if not local_db.is_file():
        raise SystemExit(f"ERROR: no existe {local_db}")

    data = _fetch(DEFAULT_TABLES)
    if not data.get("ok"):
        raise SystemExit(f"ERROR: {data}")

    print("Conteos en Render:", data.get("counts"))
    backup = _backup_local(local_db)
    print(f"Backup local: {backup}")
    applied = _apply_to_sqlite(local_db, data.get("tables") or {})
    print("Aplicado en local:")
    for table, n in applied.items():
        print(f"  {table}: {n}")
    print("Listo. Recargá http://127.0.0.1:5000/gos/objetivos/")


if __name__ == "__main__":
    main()
