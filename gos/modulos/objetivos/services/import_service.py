"""Importa datos desde SQLite (local o archivo subido) hacia la base activa.

Protecciones anti-wipe:
- Antes de TRUNCATE CASCADE, snapshot de tablas protegidas en el destino.
- Si el origen trae 0 filas (o no trae la tabla) y el destino tiene datos,
  se restauran después del import. Así un SQLite local vacío no borra
  Capacitación / perfiles / O&M / etc. que solo vivían en Render.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

# Orden de inserción (padres antes que hijos).
TABLES = [
    "empresas",
    "planeamiento_config",
    "sectores",
    "areas",
    "responsables",
    "perfiles",
    "usuarios",
    "foda_documentos",
    "foda_items",
    "dafo_tareas",
    "objetivos",
    "kpi_indicadores",
    # Mantenimiento
    "mant_unidades",
    "mant_plan_meta",
    "mant_plan_celdas",
    "mant_vtv",
    "mant_vtv_turnos",
    "mant_reporte_ordenes",
    "mant_reporte_tareas",
    "mant_reporte_solicitudes",
    # Capacitación (padres → hijos)
    "cap_config",
    "cap_centros",
    "cap_puestos",
    "cap_taxonomia_items",
    "cap_empresas_capacitadoras",
    "cap_instructores",
    "cap_certificacion_tipos",
    "cap_cursos",
    "cap_participantes",
    "cap_programas",
    "cap_planes",
    "cap_programa_planes",
    "cap_plan_cursos",
    "cap_programa_puestos",
    "cap_encuentros",
    "cap_encuentro_temas",
    "cap_cronograma_puestos",
    "cap_inscripciones",
    "cap_asistencias",
    "cap_registros",
    "cap_certificaciones",
    "cap_requisitos",
    "cap_acreditaciones",
    "cap_alertas",
    # O&M
    "om_modules",
    "om_module_personnel",
    "om_personnel_phones",
    "om_module_items",
    "om_audit_log",
    # Análisis / Vacaciones / Ralentí
    "hwo_datasets",
    "hwo_modalidad",
    "registros",
    "vacaciones",
    "tot_hs",
    "ralenti_files",
    "ralenti_events",
    "ralenti_config",
]

# Nunca reemplazar con un origen vacío: si Render tiene filas y el SQLite no, se conservan.
PROTECTED_TABLES = frozenset(
    {
        "perfiles",
        "usuarios",
        *[t for t in TABLES if t.startswith("cap_")],
        *[t for t in TABLES if t.startswith("om_")],
        "hwo_datasets",
        "hwo_modalidad",
        # Objetivos / FODA / catálogos (no pisar con SQLite vacío)
        "sectores",
        "areas",
        "responsables",
        "objetivos",
        "kpi_indicadores",
        "foda_documentos",
        "foda_items",
        "dafo_tareas",
    }
)


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
    import gos.models  # noqa: F401
    import gos.modulos.capacitacion.models  # noqa: F401
    import gos.modulos.hwo.models  # noqa: F401
    import gos.modulos.mantenimiento.models  # noqa: F401
    import gos.modulos.objetivos.models  # noqa: F401
    import gos.modulos.om.models  # noqa: F401
    import gos.modulos.ralenti.models  # noqa: F401
    import gos.modulos.vacaciones.models  # noqa: F401
    from gos.extensions import db

    engine = create_engine(fix_postgres_url(target_url))
    db.Model.metadata.create_all(engine)
    engine.dispose()


def _tables_present(connection, tables: list[str]) -> list[str]:
    existing = set(inspect(connection).get_table_names())
    return [table for table in tables if table in existing]


def _count_table(connection, table: str) -> int:
    return int(connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0)


def _snapshot_tables(connection, tables: list[str]) -> dict[str, list[dict]]:
    snaps: dict[str, list[dict]] = {}
    existing = set(inspect(connection).get_table_names())
    for table in tables:
        if table not in existing:
            continue
        rows = connection.execute(text(f'SELECT * FROM "{table}"')).mappings().all()
        snaps[table] = [dict(row) for row in rows]
    return snaps


def _restore_snapshots(connection, snaps: dict[str, list[dict]]) -> None:
    """Reinserta filas preservadas (tablas ya vacías tras CASCADE)."""
    inspector = inspect(connection)
    for table in TABLES:
        rows = snaps.get(table) or []
        if not rows:
            continue
        physical_cols = {c["name"] for c in inspector.get_columns(table)}
        batch = 500
        for i in range(0, len(rows), batch):
            chunk = []
            for row in rows[i : i + batch]:
                chunk.append({k: v for k, v in row.items() if k in physical_cols})
            if not chunk:
                continue
            cols = sorted({k for row in chunk for k in row})
            if not cols:
                continue
            col_sql = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join(f":{c}" for c in cols)
            stmt = text(
                f'INSERT INTO "{table}" ({col_sql}) VALUES ({placeholders})'
            )
            connection.execute(stmt, chunk)
        _reset_sequences(connection, table)


def _clear_tables(connection, tables: list[str]) -> None:
    """Vacía tablas del import. En Postgres usa CASCADE (Render no da replication_role)."""
    to_clear = _tables_present(connection, tables)
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


def _tables_to_preserve(
    src_counts: dict[str, int],
    tgt_conn,
) -> list[str]:
    """Tablas protegidas que no deben reducirse: destino tiene más filas que el origen."""
    present = set(inspect(tgt_conn).get_table_names())
    preserve: list[str] = []
    for table in TABLES:
        if table not in PROTECTED_TABLES or table not in present:
            continue
        src_n = src_counts.get(table, 0)
        tgt_n = _count_table(tgt_conn, table)
        if tgt_n > src_n:
            preserve.append(table)
    return preserve


def importar_tablas_json(tables_data: dict[str, list], target_url: str) -> dict[str, int]:
    """Reemplaza solo las tablas pedidas (JSON). No toca el resto de la base.

    Remapea empresa_id al primer id de empresas en destino cuando hace falta.
    """
    import gos.modulos.objetivos.models  # noqa: F401
    from gos.extensions import db

    if not isinstance(tables_data, dict) or not tables_data:
        raise ValueError("tables_data vacío")

    ordered = [t for t in TABLES if t in tables_data]
    unknown = sorted(set(tables_data) - set(TABLES))
    if unknown:
        raise ValueError(f"Tablas no permitidas: {', '.join(unknown)}")
    if not ordered:
        raise ValueError("Ninguna tabla válida")

    target_url = fix_postgres_url(target_url)
    _ensure_schema(target_url)
    tgt_engine = create_engine(target_url)
    imported: dict[str, int] = {}

    with tgt_engine.begin() as tgt_conn:
        empresa_id = tgt_conn.execute(
            text('SELECT id FROM "empresas" ORDER BY id LIMIT 1')
        ).scalar()
        if empresa_id is None and "empresas" not in tables_data:
            raise ValueError("No hay empresa en destino y no se envió tabla empresas")

        for table in ordered:
            rows = tables_data.get(table) or []
            if not isinstance(rows, list):
                raise ValueError(f"{table}: se esperaba una lista de filas")

            # Solo vaciar esta tabla (sin CASCADE masivo).
            if tgt_conn.dialect.name == "postgresql":
                tgt_conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY'))
            else:
                tgt_conn.execute(text(f'DELETE FROM "{table}"'))

            if not rows:
                imported[table] = 0
                continue

            physical_cols = {c["name"] for c in inspect(tgt_conn).get_columns(table)}
            model_table = db.Model.metadata.tables.get(table)
            model_cols = {c.name for c in model_table.columns} if model_table is not None else physical_cols
            allowed = physical_cols & model_cols

            is_sqlite = tgt_conn.dialect.name == "sqlite"
            prepared: list[dict] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                item = {k: v for k, v in row.items() if k in allowed}
                if "valores_mes" in item and isinstance(item["valores_mes"], str):
                    try:
                        item["valores_mes"] = json.loads(item["valores_mes"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                # SQLite no acepta dict/list en binds; Postgres JSON sí.
                if is_sqlite:
                    for key, value in list(item.items()):
                        if isinstance(value, (dict, list)):
                            item[key] = json.dumps(value, ensure_ascii=False)
                if (
                    empresa_id is not None
                    and "empresa_id" in allowed
                    and table != "empresas"
                ):
                    item["empresa_id"] = int(empresa_id)
                # Dejar que el destino asigne ids nuevos si vienen del SQLite local.
                item.pop("id", None)
                prepared.append(item)

            batch = 500
            for i in range(0, len(prepared), batch):
                chunk = prepared[i : i + batch]
                if not chunk:
                    continue
                cols = sorted({k for row in chunk for k in row})
                col_sql = ", ".join(f'"{c}"' for c in cols)
                placeholders = ", ".join(f":{c}" for c in cols)
                stmt = text(
                    f'INSERT INTO "{table}" ({col_sql}) VALUES ({placeholders})'
                )
                tgt_conn.execute(stmt, chunk)

            _reset_sequences(tgt_conn, table)
            imported[table] = len(prepared)

    return imported


def importar_sqlite(local_path: Path, target_url: str) -> dict[str, int]:
    import gos.modulos.capacitacion.models  # noqa: F401
    import gos.modulos.hwo.models  # noqa: F401
    import gos.modulos.mantenimiento.models  # noqa: F401
    import gos.modulos.objetivos.models  # noqa: F401
    import gos.modulos.om.models  # noqa: F401
    import gos.modulos.ralenti.models  # noqa: F401
    import gos.modulos.vacaciones.models  # noqa: F401
    from gos.extensions import db

    local_path = Path(local_path)
    if not local_path.is_file():
        raise FileNotFoundError(f"No existe {local_path}")

    target_url = fix_postgres_url(target_url)
    source_url = f"sqlite:///{local_path.as_posix()}"

    src_engine = create_engine(source_url)
    tgt_engine = create_engine(target_url)

    with src_engine.connect() as src_conn:
        tables = _tables_present(src_conn, TABLES)

    src_meta = MetaData()
    if tables:
        src_meta.reflect(bind=src_engine, only=tables)

    _ensure_schema(target_url)
    source_counts: dict[str, int] = {table: 0 for table in TABLES}
    preserved: list[str] = []

    with src_engine.connect() as src_conn:
        staged: dict[str, list[dict]] = {}
        for table in tables:
            rows = src_conn.execute(src_meta.tables[table].select()).mappings().all()
            source_counts[table] = len(rows)
            staged[table] = [_row_dict(row) for row in rows]

        with tgt_engine.begin() as tgt_conn:
            preserve = _tables_to_preserve(source_counts, tgt_conn)
            snaps = _snapshot_tables(tgt_conn, preserve) if preserve else {}
            preserved = [t for t, rows in snaps.items() if rows]

            _clear_tables(tgt_conn, tables)
            tgt_inspector = inspect(tgt_conn)
            for table in tables:
                payload = staged[table]
                if not payload:
                    continue
                # Tabla preservada: no insertar origen (se restaura el snapshot).
                if table in snaps:
                    continue
                tgt_table = db.Model.metadata.tables[table]
                physical_cols = {c["name"] for c in tgt_inspector.get_columns(table)}
                model_cols = {c.name for c in tgt_table.columns}
                allowed = physical_cols & model_cols
                filtered = [
                    {k: v for k, v in row.items() if k in allowed} for row in payload
                ]
                if not filtered:
                    continue
                batch = 1000
                for i in range(0, len(filtered), batch):
                    chunk = filtered[i : i + batch]
                    # Insertar solo columnas presentes en el destino físico.
                    cols = sorted({k for row in chunk for k in row})
                    if not cols:
                        continue
                    col_sql = ", ".join(f'"{c}"' for c in cols)
                    placeholders = ", ".join(f":{c}" for c in cols)
                    stmt = text(
                        f'INSERT INTO "{table}" ({col_sql}) VALUES ({placeholders})'
                    )
                    tgt_conn.execute(stmt, chunk)

            if snaps:
                to_restore = {t: rows for t, rows in snaps.items() if rows}
                _restore_snapshots(tgt_conn, to_restore)

            for table in tables:
                _reset_sequences(tgt_conn, table)

    expected = {
        k: v for k, v in source_counts.items() if k in tables and v > 0 and k not in preserved
    }
    verify_counts(expected, target_url)
    if preserved:
        print(
            "Preservadas en destino (origen tenía menos filas): " + ", ".join(preserved),
            file=sys.stderr,
        )
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
