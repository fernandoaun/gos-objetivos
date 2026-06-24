"""Sube instance/gos_objetivos.db a Render para importar en la base del servicio web."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
LOCAL_DB = ROOT / "instance" / "gos_objetivos.db"
DEFAULT_URL = "https://gos-objetivos.onrender.com"


def main() -> None:
    secret = os.environ.get("GOS_IMPORT_SECRET", "").strip()
    base_url = os.environ.get("GOS_RENDER_URL", DEFAULT_URL).rstrip("/")
    if not secret:
        print("ERROR: definí GOS_IMPORT_SECRET (Render → gos-objetivos → Environment).")
        sys.exit(1)
    if not LOCAL_DB.is_file():
        print(f"ERROR: no existe {LOCAL_DB}")
        sys.exit(1)

    boundary = "----GOSBoundary7MA4YWxkTrZu0gW"
    db_bytes = LOCAL_DB.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="database"; filename="gos_objetivos.db"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + db_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/api/v1/admin/import-db",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Import-Secret": secret,
        },
    )

    print(f"Subiendo {LOCAL_DB.name} ({len(db_bytes) // 1024} KB) a {base_url} ...")
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
