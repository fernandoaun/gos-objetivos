"""Importa datos desde SQLite (local o archivo subido) hacia la base activa."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import MetaData, create_engine, insert, inspect, text
from sqlalchemy.exc import SQLAlchemyError

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


def fix_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _row_dict(row) -> dict:
    data = dict(row)
    for key, value in data.items():
        if isinstance(value, str) and key in ("valores_mes",):
            try:
                data[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
    return data


def _ensure_schema(target_url: str) -> None:
    import gos.modulos.objetivos.models  # noqa: F401
    from gos.extensions import db

    engine = create_engine(fix_postgres_url(target_url))
    db.Model.metadata.create_all(engine)
    engine.dispose()


def _clear_tables(connection) -> None:
    from sqlalchemy import inspect, text

    existing = set(inspect(connection).get_table_names())
    to_clear = [table for table in TABLES if table in existing]
    if not to_clear:
        return

    if connection.dialect.name == "postgresql":
        tables_sql = ", ".join(f'"{table}"' for table in to_clear)
        connection.execute(
            text(f"TRUNCATE TABLE {tables_sql} RESTART IDENTITY CASCADE")
        )
        return

    connection.execute(text("PRAGMA foreign_keys = OFF"))
    for table in reversed(to_clear):
        connection.execute(text(f'DELETE FROM "{table}"'))
    connection.execute(text("PRAGMA foreign_keys = ON"))


def _reset_sequences(connection, table: str) -> None:
    if connection.dialect.name != "postgresql":
        return
    seq = connection.execute(
        text("SELECT pg_get_serial_sequence(:table, 'id')"),
        {"table": f"public.{table}"},
    ).scalar()
    if not seq:
        return
    connection.execute(
        text(f'SELECT setval(:seq, COALESCE((SELECT MAX(id) FROM "{table}"), 1), true)'),
        {"seq": seq},
    )


def importar_sqlite(local_path: Path, target_url: str) -> dict[str, int]:
    import gos.modulos.objetivos.models  # noqa: F401
    from gos.extensions import db

    local_path = Path(local_path)
    if not local_path.is_file():
        raise FileNotFoundError(f"No existe {local_path}")

    target_url = fix_postgres_url(target_url)
    source_url = f"sqlite:///{local_path.as_posix()}"

    src_engine = create_engine(source_url)
    tgt_engine = create_engine(target_url)
    src_meta = MetaData()
    src_meta.reflect(bind=src_engine, only=TABLES)

    _ensure_schema(target_url)
    source_counts: dict[str, int] = {}

    with src_engine.connect() as src_conn:
        staged: dict[str, list[dict]] = {}
        for table in TABLES:
            rows = src_conn.execute(src_meta.tables[table].select()).mappings().all()
            source_counts[table] = len(rows)
            staged[table] = [_row_dict(row) for row in rows]

        with tgt_engine.begin() as tgt_conn:
            _clear_tables(tgt_conn)
            for table in TABLES:
                payload = staged[table]
                if not payload:
                    continue
                tgt_table = db.Model.metadata.tables[table]
                tgt_conn.execute(insert(tgt_table), payload)
            for table in TABLES:
                _reset_sequences(tgt_conn, table)

    verify_counts(source_counts, target_url)
    return source_counts


def verify_counts(expected: dict[str, int], target_url: str) -> None:
    engine = create_engine(fix_postgres_url(target_url))
    with engine.connect() as conn:
        for table, exp in expected.items():
            if exp == 0:
                continue
            got = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0
            if got != exp:
                raise RuntimeError(f"Verificación falló en {table}: {got} != {exp}")
    engine.dispose()


def importar_sqlite_or_exit(local_path: Path, target_url: str) -> None:
    try:
        counts = importar_sqlite(local_path, target_url)
    except (SQLAlchemyError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Origen : {local_path} ({local_path.stat().st_size // 1024} KB)")
    print("Importación completa y verificada:")
    for table, n in counts.items():
        if n:
            print(f"  {table}: {n} filas")
