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


def _ensure_target_schema(target_url: str) -> None:
    from sqlalchemy import create_engine

    import app.models  # noqa: F401 — registrar tablas en metadata
    from app.extensions import db

    engine = create_engine(_fix_postgres_url(target_url))
    db.Model.metadata.create_all(engine)
    engine.dispose()


def _clear_target_tables(connection) -> None:
    from sqlalchemy import inspect, text

    existing = set(inspect(connection).get_table_names())
    to_clear = [table for table in TABLES if table in existing]
    if not to_clear:
        return
    tables_sql = ", ".join(f'"{table}"' for table in to_clear)
    connection.execute(
        text(f"TRUNCATE TABLE {tables_sql} RESTART IDENTITY CASCADE")
    )


def _reset_sequences(connection, table: str) -> None:
    from sqlalchemy import text

    seq = connection.execute(
        text("SELECT pg_get_serial_sequence(:table, 'id')"),
        {"table": f"public.{table}"},
    ).scalar()
    if not seq:
        return
    connection.execute(
        text(
            f'SELECT setval(:seq, COALESCE((SELECT MAX(id) FROM "{table}"), 1), true)'
        ),
        {"seq": seq},
    )


def _row_dict(row) -> dict:
    import json

    data = dict(row)
    for key, value in data.items():
        if isinstance(value, str) and key in ("valores_mes",):
            try:
                data[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
    return data


def _verify_import(source_counts: dict[str, int], target_url: str) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(_fix_postgres_url(target_url))
    with engine.connect() as conn:
        print("  Verificando en Render...")
        for table, expected in source_counts.items():
            if expected == 0:
                continue
            got = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0
            status = "OK" if got == expected else "ERROR"
            print(f"    {table}: {got} (esperado {expected}) [{status}]")
            if got != expected:
                print("ERROR: la importacion no coincidio. Revisa la URL de la base gos-objetivos-db.")
                sys.exit(1)
    engine.dispose()


def importar(local_path: Path, target_url: str) -> None:
    from sqlalchemy import MetaData, create_engine, insert

    if not local_path.is_file():
        print(f"ERROR: no existe la base local {local_path}")
        sys.exit(1)

    source_url = f"sqlite:///{local_path.as_posix()}"
    target_url = _fix_postgres_url(target_url)

    import app.models  # noqa: F401
    from app.extensions import db

    src_engine = create_engine(source_url)
    tgt_engine = create_engine(target_url)

    src_meta = MetaData()
    src_meta.reflect(bind=src_engine, only=TABLES)

    print(f"Origen : {local_path} ({local_path.stat().st_size // 1024} KB)")
    print("Destino: PostgreSQL (Render)")
    print("  Creando tablas en Render (si no existen)...")
    _ensure_target_schema(target_url)

    source_counts: dict[str, int] = {}

    with src_engine.connect() as src_conn:
        with tgt_engine.begin() as tgt_conn:
            print("  Limpiando datos anteriores en Render...")
            _clear_target_tables(tgt_conn)

            for table in TABLES:
                src_table = src_meta.tables[table]
                tgt_table = db.Model.metadata.tables[table]
                rows = src_conn.execute(src_table.select()).mappings().all()
                source_counts[table] = len(rows)
                if not rows:
                    print(f"  {table}: 0 filas")
                    continue
                payload = [_row_dict(row) for row in rows]
                tgt_conn.execute(insert(tgt_table), payload)
                print(f"  {table}: {len(rows)} filas")

            for table in TABLES:
                _reset_sequences(tgt_conn, table)

    _verify_import(source_counts, target_url)
    print("Importación completa y verificada.")


def main() -> None:
    target_url = os.environ.get("RENDER_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not target_url or not target_url.startswith(("postgres://", "postgresql://")):
        print("ERROR: definí RENDER_DATABASE_URL con la URL externa de PostgreSQL en Render.")
        sys.exit(1)
    if "..." in target_url or "tu URL" in target_url.lower():
        print("ERROR: pegaste el texto de ejemplo, no la URL real de Render.")
        print("Copiala en Render → gos-objetivos-db → Connections → External Database URL")
        sys.exit(1)
    try:
        import psycopg2  # noqa: F401
    except ModuleNotFoundError:
        print("ERROR: falta psycopg2. Ejecutá: python -m pip install psycopg2-binary")
        sys.exit(1)
    importar(LOCAL_DB, target_url)


if __name__ == "__main__":
    main()
