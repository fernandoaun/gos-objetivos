"""Baja el estado actual de Render y lo carga en instance/prueba/ (solo local).

No modifica Render. No toca instance/gos.db principal.

Uso:
  python scripts/bajar_render_a_prueba.py
"""
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
from gos.modulos.objetivos.services.import_service import TABLES

API_PATH = "/gos/objetivos/api/v1/admin/export-tables"
PRUEBA_DIR = ROOT / "instance" / "prueba"
PRUEBA_DB = PRUEBA_DIR / "gos.db"
BACKUP_DIR = ROOT / "instance" / "backups"


def _fetch_all() -> dict:
    secret = env.import_secret()
    base = env.render_service_url().rstrip("/")
    if not secret:
        raise SystemExit("ERROR: definí GOS_IMPORT_SECRET en .env")
    body = json.dumps({"tables": list(TABLES)}).encode("utf-8")
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
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"
        ) from exc


def _backup(db_path: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"prueba-pre-pull-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    shutil.copy2(db_path, dest)
    return dest


def _apply(db_path: Path, tables_data: dict[str, list]) -> dict[str, int]:
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
                for k, v in list(filtered.items()):
                    if isinstance(v, (dict, list)):
                        filtered[k] = json.dumps(v, ensure_ascii=False)
                    elif isinstance(v, bool):
                        filtered[k] = int(v)
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


def _ensure_local_admins() -> None:
    """Garantiza auto-login / login demo en la base de prueba."""
    from wsgi import app
    from gos.extensions import db
    from gos.models import Empresa, Usuario

    with app.app_context():
        # Forzar URI de prueba por si el proceso no tiene GOS_DATABASE_PATH
        empresa = Empresa.query.filter_by(activa=True).first()
        if not empresa:
            empresa = Empresa(nombre=env.dev_empresa_nombre(), activa=True)
            db.session.add(empresa)
            db.session.flush()

        for email, password, nombre, rol in (
            (
                env.dev_login_email(),
                env.dev_login_password(),
                env.dev_login_nombre(),
                "administrador",
            ),
            (
                env.admin_email(),
                env.admin_password(),
                env.admin_nombre(),
                "administrador",
            ),
        ):
            user = Usuario.query.filter_by(email=email).first()
            if user:
                user.set_password(password)
                user.activo = True
                user.rol = rol
            else:
                user = Usuario(
                    empresa_id=empresa.id,
                    email=email,
                    nombre=nombre,
                    rol=rol,
                    activo=True,
                )
                user.set_password(password)
                db.session.add(user)
        db.session.commit()
        print(
            f"Admins locales OK: {env.dev_login_email()}, {env.admin_email()}"
        )


def main() -> None:
    if not PRUEBA_DB.is_file():
        print("No hay base de prueba. Creando copia local primero...")
        from scripts.preparar_local_prueba import prepare

        prepare(desde_snapshot=False, reset=True)

    print(f"Destino: {PRUEBA_DB}")
    data = _fetch_all()
    if not data.get("ok"):
        raise SystemExit(f"ERROR: {data}")

    counts = data.get("counts") or {}
    nonempty = {k: v for k, v in counts.items() if v}
    print("Conteos en Render (con datos):")
    for table, n in sorted(nonempty.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {table}: {n}")

    backup = _backup(PRUEBA_DB)
    print(f"Backup previo de prueba: {backup}")

    applied = _apply(PRUEBA_DB, data.get("tables") or {})
    print("Aplicado en instance/prueba:")
    for table, n in sorted(applied.items(), key=lambda x: (-x[1], x[0])):
        if n:
            print(f"  {table}: {n}")

    # Asegurar admins con la app apuntando a la DB de prueba
    import os

    os.environ["GOS_DATABASE_PATH"] = str(PRUEBA_DB)
    os.environ.pop("DATABASE_URL", None)
    os.environ["FLASK_ENV"] = "development"
    _ensure_local_admins()

    meta = PRUEBA_DIR / "ORIGEN.txt"
    meta.write_text(
        "\n".join(
            [
                f"Actualizado desde Render: {datetime.now().isoformat(timespec='seconds')}",
                f"URL: {env.render_service_url()}",
                f"Tablas con datos: {len(nonempty)}",
                "",
                "Solo local — no se modificó Render.",
                "Abrir: ABRIR LOCAL PRUEBA.bat → http://127.0.0.1:5001/",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print()
    print("Listo. Reiniciá ABRIR LOCAL PRUEBA.bat y abrí http://127.0.0.1:5001/")


if __name__ == "__main__":
    main()
