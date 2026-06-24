"""
Copia todos los datos del SQLite local a PostgreSQL (Render).

Uso (PowerShell, una sola línea con la URL externa de Render):
  $env:RENDER_DATABASE_URL="postgresql://..."
  python scripts/importar_local_a_render.py

La URL está en Render → gos-objetivos-db → Connections → External Database URL
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOCAL_DB = ROOT / "instance" / "gos_objetivos.db"

# Orden respetando claves foráneas
TABLES = [
    "empresas",
    "planeamiento_config",
    "sectores",
    "areas",
    "responsables",
    "usuarios",
    "foda_documentos",
    "foda_items",
    "dafo_tareas",
    "objetivos",
    "kpi_indicadores",
]


def _fix_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _reset_sequences(connection, table: str) -> None:
    from sqlalchemy import text

    seq = connection.execute(
        text(
            "SELECT pg_get_serial_sequence(:table, 'id')"
        ),
        {"table": table},
    ).scalar()
    if not seq:
        return
    connection.execute(
        text(f"SELECT setval(:seq, COALESCE((SELECT MAX(id) FROM {table}), 1), true)"),
        {"seq": seq},
    )


def importar(local_path: Path, target_url: str) -> None:
    from sqlalchemy import MetaData, create_engine, insert, text

    if not local_path.is_file():
        print(f"ERROR: no existe la base local {local_path}")
        sys.exit(1)

    source_url = f"sqlite:///{local_path.as_posix()}"
    target_url = _fix_postgres_url(target_url)

    src_engine = create_engine(source_url)
    tgt_engine = create_engine(target_url)

    src_meta = MetaData()
    src_meta.reflect(bind=src_engine, only=TABLES)

    print(f"Origen : {local_path} ({local_path.stat().st_size // 1024} KB)")
    print("Destino: PostgreSQL (Render)")

    with src_engine.connect() as src_conn:
        with tgt_engine.begin() as tgt_conn:
            tgt_conn.execute(text("SET session_replication_role = 'replica'"))
            for table in reversed(TABLES):
                tgt_conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))
            tgt_conn.execute(text("SET session_replication_role = 'origin'"))

            for table in TABLES:
                table_obj = src_meta.tables[table]
                rows = src_conn.execute(table_obj.select()).mappings().all()
                if not rows:
                    print(f"  {table}: 0 filas")
                    continue
                tgt_conn.execute(insert(table_obj), [dict(row) for row in rows])
                print(f"  {table}: {len(rows)} filas")

            for table in TABLES:
                _reset_sequences(tgt_conn, table)

    print("Importación completa.")


def main() -> None:
    target_url = os.environ.get("RENDER_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not target_url or not target_url.startswith(("postgres://", "postgresql://")):
        print("ERROR: definí RENDER_DATABASE_URL con la URL externa de PostgreSQL en Render.")
        sys.exit(1)
    importar(LOCAL_DB, target_url)


if __name__ == "__main__":
    main()
