"""Sube solo tablas de ralentí del SQLite local a Render (JSON, no toca Capacitación)."""
from __future__ import annotations

import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv()

from gos import env

API_PATH = "/gos/objetivos/api/v1/admin/import-tables"
TABLES = ("ralenti_files", "ralenti_events", "ralenti_config")


def _local_rows(db_path: Path, table: str) -> list[dict]:
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(f'SELECT * FROM "{table}"').fetchall()]
    finally:
        conn.close()


def main() -> None:
    secret = env.import_secret()
    base = env.render_service_url().rstrip("/")
    local_db = env.local_backup_db_path()
    if not secret:
        raise SystemExit("ERROR: definí GOS_IMPORT_SECRET en .env")
    if not local_db.is_file():
        raise SystemExit(f"ERROR: no existe {local_db}")

    tables: dict[str, list] = {}
    for table in TABLES:
        rows = _local_rows(local_db, table)
        tables[table] = rows
        print(f"  {table}: {len(rows)} filas")

    body = json.dumps({"tables": tables}, ensure_ascii=False).encode("utf-8")
    print(f"Payload: {len(body) // 1024} KB -> {base}{API_PATH}")
    req = urllib.request.Request(
        f"{base}{API_PATH}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Import-Secret": secret,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:2000]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"ERROR de conexión: {exc.reason}") from exc

    if not payload.get("ok"):
        raise SystemExit(f"ERROR: {payload}")
    print("OK imported:", payload.get("imported"))


if __name__ == "__main__":
    main()
