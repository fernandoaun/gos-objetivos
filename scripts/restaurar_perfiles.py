"""Restaura perfiles base en local y/o los sube a Render (sin wipe de otras tablas)."""
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

from gos import create_app, env
from gos.models import Empresa
from gos.services import perfil_service

API_PATH = "/gos/objetivos/api/v1/admin/upsert-perfiles"


def restaurar_local() -> dict:
    app = create_app()
    with app.app_context():
        empresa = Empresa.query.order_by(Empresa.id).first()
        if not empresa:
            raise SystemExit("ERROR: no hay empresa en la base local.")
        result = perfil_service.restaurar_perfiles_base(empresa.id)
        export = perfil_service.exportar_perfiles_empresa(empresa.id)
        return {"empresa_id": empresa.id, **result, "perfiles": export}


def subir_a_render(perfiles: list[dict] | None = None) -> dict:
    secret = env.import_secret()
    base_url = env.render_service_url().rstrip("/")
    if not secret:
        raise SystemExit("ERROR: definí GOS_IMPORT_SECRET en .env")
    body = json.dumps({"perfiles": perfiles or list(perfil_service.PERFILES_BASE)}).encode(
        "utf-8"
    )
    req = urllib.request.Request(
        f"{base_url}{API_PATH}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Import-Secret": secret,
        },
    )
    print(f"Subiendo perfiles a {base_url}{API_PATH} ...")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc


def main() -> None:
    args = set(sys.argv[1:])
    do_local = not args or "--local" in args or "--all" in args
    do_render = "--render" in args or "--all" in args

    if do_local:
        local = restaurar_local()
        print("Local OK:")
        print(json.dumps(local, ensure_ascii=False, indent=2))

    if do_render:
        remote = subir_a_render()
        print("Render OK:")
        print(json.dumps(remote, ensure_ascii=False, indent=2))

    if not do_local and not do_render:
        print("Uso: python scripts/restaurar_perfiles.py [--local] [--render] [--all]")
        sys.exit(1)


if __name__ == "__main__":
    main()
