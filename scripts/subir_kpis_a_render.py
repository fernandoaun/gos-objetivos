"""Sube solo kpi_indicadores del SQLite local a Render (JSON, sin wipe del resto)."""
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
TABLE = "kpi_indicadores"


def _local_rows(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f'SELECT * FROM "{TABLE}"').fetchall()
        out: list[dict] = []
        for row in rows:
            item = dict(row)
            vm = item.get("valores_mes")
            if isinstance(vm, str) and vm:
                try:
                    item["valores_mes"] = json.loads(vm)
                except json.JSONDecodeError:
                    pass
            out.append(item)
        return out
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

    rows = _local_rows(local_db)
    print(f"Origen: {local_db} — {len(rows)} KPIs")
    if not rows:
        raise SystemExit("ERROR: no hay filas en kpi_indicadores local")

    body = json.dumps({"tables": {TABLE: rows}}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base}{API_PATH}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Import-Secret": secret,
        },
    )
    print(f"Subiendo a {base}{API_PATH} ...")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"
        ) from exc

    if not payload.get("ok"):
        raise SystemExit(f"ERROR: {payload}")
    print("OK:", payload.get("imported"))


if __name__ == "__main__":
    main()
