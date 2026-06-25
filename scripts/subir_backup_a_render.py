"""Sube un backup SQLite local a Render para importar en la base del servicio web."""
from __future__ import annotations

import sys
from pathlib import Path

import urllib.error
import urllib.request
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv()

from gos import env

API_PATH = "/gos/objetivos/api/v1/admin/import-db"


def main() -> None:
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
