"""Sube el JSON legacy de O&M a Render (idempotente por code)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv()

from gos import env

API_PATH = "/gos/om/api/admin/import-legacy"
DEFAULT_FILE = ROOT / "gos" / "modulos" / "om" / "data" / "modulos_data.legacy.json"


def main() -> None:
    secret = env.import_secret()
    base_url = env.render_service_url().rstrip("/")
    file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FILE

    if not secret:
        print("ERROR: definí GOS_IMPORT_SECRET en .env")
        sys.exit(1)
    if not file_path.is_file():
        print(f"ERROR: no existe {file_path}")
        sys.exit(1)

    payload = file_path.read_bytes()
    # Validar JSON
    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, list):
        print("ERROR: el archivo debe ser un array JSON de módulos")
        sys.exit(1)

    req = urllib.request.Request(
        f"{base_url}{API_PATH}",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Import-Secret": secret,
        },
    )

    print(f"Subiendo {len(data)} módulos O&M a {base_url}{API_PATH} ...")
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
