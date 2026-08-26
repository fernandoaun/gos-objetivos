"""Exporta el módulo Capacitación + datos a un paquete entregable.

NO modifica la base de origen (solo lectura). NO toca Render.
NO escribe en instance/gos.db ni en instance/prueba/gos.db.

Incluye:
  - SQLite solo con tablas cap_* + empresas/sectores/responsables
  - Copia del código gos/modulos/capacitacion (sin __pycache__)
  - Archivos de storage/capacitacion si existen
  - MANIFEST.json + README para el equipo receptor
  - ZIP final listo para compartir

Uso:
  python scripts/exportar_capacitacion_paquete.py
  python scripts/exportar_capacitacion_paquete.py --source instance/prueba/gos.db
  python scripts/exportar_capacitacion_paquete.py --from-render
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EXPORTS_ROOT = ROOT / "exports"
MODULE_SRC = ROOT / "gos" / "modulos" / "capacitacion"
STORAGE_SRC = ROOT / "storage" / "capacitacion"

PARENT_TABLES = (
    "empresas",
    "perfiles",
    "usuarios",
    "sectores",
    "areas",
    "responsables",
)
SKIP_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".git"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def _candidates() -> list[Path]:
    return [
        ROOT / "instance" / "prueba" / "gos.db",
        ROOT / "instance" / "gos.db",
        ROOT / "instance" / "gos_objetivos.db",
    ]


def _cap_row_total(db_path: Path) -> int:
    if not db_path.is_file():
        return -1
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        names = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'cap_%'"
            )
        ]
        total = 0
        for name in names:
            total += conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        return total
    finally:
        conn.close()


def _pick_source(explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.is_file():
            raise SystemExit(f"ERROR: no existe la base fuente: {explicit}")
        return explicit.resolve()
    scored = [(p, _cap_row_total(p)) for p in _candidates() if p.is_file()]
    if not scored:
        raise SystemExit("ERROR: no hay ninguna gos.db local para exportar.")
    scored.sort(key=lambda x: x[1], reverse=True)
    best, rows = scored[0]
    if rows <= 0:
        print(
            "AVISO: la mejor base local tiene 0 filas en cap_*. "
            "Se exporta igual (esquema + tablas padre)."
        )
    print(f"Fuente elegida: {best.relative_to(ROOT)} ({rows} filas cap_*)")
    return best


def _list_export_tables(conn: sqlite3.Connection) -> list[str]:
    existing = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    caps = sorted(n for n in existing if n.startswith("cap_"))
    parents = [t for t in PARENT_TABLES if t in existing]
    missing_parents = [t for t in PARENT_TABLES if t not in existing]
    if missing_parents:
        print(f"AVISO: tablas padre ausentes en origen: {', '.join(missing_parents)}")
    if not caps:
        raise SystemExit("ERROR: no hay tablas cap_* en la base fuente.")
    # Padres primero (FKs), luego cap_* en orden alfabético estable.
    return parents + caps


def _copy_schema_and_data(src_path: Path, dest_path: Path) -> dict[str, int]:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        dest_path.unlink()

    src = sqlite3.connect(f"file:{src_path.as_posix()}?mode=ro", uri=True)
    dest = sqlite3.connect(dest_path.as_posix())
    counts: dict[str, int] = {}
    try:
        tables = _list_export_tables(src)
        dest.execute("PRAGMA foreign_keys = OFF")
        for table in tables:
            row = src.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not row or not row[0]:
                print(f"  skip {table}: sin DDL")
                continue
            dest.execute(row[0])
            cols = [r[1] for r in src.execute(f'PRAGMA table_info("{table}")')]
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join("?" for _ in cols)
            rows = src.execute(f'SELECT {col_list} FROM "{table}"').fetchall()
            if rows:
                dest.executemany(
                    f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
                    rows,
                )
            counts[table] = len(rows)
            print(f"  {table}: {len(rows)} filas")

        # Índices / unique no cubiertos por CREATE TABLE
        for table in tables:
            for idx_sql, in src.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' "
                "AND tbl_name=? AND sql IS NOT NULL",
                (table,),
            ):
                try:
                    dest.execute(idx_sql)
                except sqlite3.Error as exc:
                    print(f"  AVISO índice en {table}: {exc}")

        # Autoincrement counters
        seq_exists = src.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
        ).fetchone()
        if seq_exists:
            dest.execute(
                "CREATE TABLE IF NOT EXISTS sqlite_sequence(name TEXT, seq INTEGER)"
            )
            for name, seq in src.execute(
                "SELECT name, seq FROM sqlite_sequence WHERE name IN (%s)"
                % (",".join("?" * len(tables))),
                tables,
            ):
                dest.execute(
                    "INSERT OR REPLACE INTO sqlite_sequence(name, seq) VALUES (?, ?)",
                    (name, seq),
                )

        dest.commit()
    finally:
        dest.close()
        src.close()
    return counts


def _copy_module(dest_dir: Path) -> int:
    if not MODULE_SRC.is_dir():
        raise SystemExit(f"ERROR: no existe el módulo: {MODULE_SRC}")
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    file_count = 0

    def _ignore(directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        for name in names:
            p = Path(directory) / name
            if name in SKIP_DIR_NAMES or name.endswith(tuple(SKIP_SUFFIXES)):
                ignored.add(name)
            elif p.is_file() and p.suffix.lower() in SKIP_SUFFIXES:
                ignored.add(name)
        return ignored

    shutil.copytree(MODULE_SRC, dest_dir, ignore=_ignore)
    for path in dest_dir.rglob("*"):
        if path.is_file():
            file_count += 1
    return file_count


def _copy_storage(dest_dir: Path) -> int:
    if not STORAGE_SRC.is_dir():
        return 0
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(STORAGE_SRC, dest_dir)
    return sum(1 for p in dest_dir.rglob("*") if p.is_file())


def _write_readme(path: Path, *, stamp: str, source: Path, counts: dict[str, int]) -> None:
    total_cap = sum(v for k, v in counts.items() if k.startswith("cap_"))
    lines = [
        "# Paquete Capacitación — GOS Objetivos",
        "",
        "Copia entregable del módulo de Capacitación **sin acceso** a producción GOS.",
        "La base y el código de origen **no se modifican** al generar este paquete.",
        "",
        "## Contenido",
        "",
        "| Ruta | Descripción |",
        "|------|-------------|",
        "| `datos/capacitacion.db` | SQLite con `cap_*` + empresas/usuarios/perfiles/sectores/areas/responsables |",
        "| `codigo/capacitacion/` | Código Flask del módulo (blueprints, models, services, static, templates) |",
        "| `storage/capacitacion/` | Evidencias/archivos subidos (si había) |",
        "| `MANIFEST.json` | Conteos y origen del export |",
        "",
        f"- Generado: `{stamp}`",
        f"- Fuente: `{source}`",
        f"- Filas totales `cap_*`: **{total_cap}**",
        "",
        "## Cómo usarlo en otro sistema",
        "",
        "1. Copiar `codigo/capacitacion/` a su árbol de módulos (equivalente a `gos/modulos/capacitacion`).",
        "2. Importar `datos/capacitacion.db` (ATTACH / migración) o reutilizar el SQLite como base de demo.",
        "3. Mapear FKs a `empresas.id` (y opcionalmente `sectores` / `responsables`) en su esquema.",
        "4. Si usan evidencias, ubicar `storage/capacitacion/` donde su app resuelva `storage/capacitacion/<empresa_id>/...`.",
        "",
        "## Qué NO incluye",
        "",
        "- Secretos (`.env`, `GOS_IMPORT_SECRET`, credenciales Render).",
        "- Otros módulos (VTV, HWO, vacaciones, ralentí, O&M, objetivos).",
        "- Acceso de escritura al GOS en Render.",
        "",
        "## Tablas incluidas",
        "",
    ]
    for name, n in sorted(counts.items()):
        lines.append(f"- `{name}`: {n}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _zip_dir(folder: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in folder.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(folder.parent).as_posix())


def _try_pull_render_to_temp(temp_db: Path) -> Path:
    """Descarga solo tablas relevantes desde Render a un SQLite temporal (no toca locals)."""
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    from gos import env
    from gos.modulos.objetivos.services.import_service import TABLES

    secret = env.import_secret()
    base = env.render_service_url().rstrip("/")
    if not secret:
        raise SystemExit("ERROR: --from-render requiere GOS_IMPORT_SECRET en .env")

    wanted = [t for t in TABLES if t.startswith("cap_") or t in PARENT_TABLES]
    # Incluir adjuntos si el endpoint los conoce en el futuro; por ahora filtramos del set TABLES.
    body = json.dumps({"tables": wanted}).encode("utf-8")
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        f"{base}/gos/objetivos/api/v1/admin/export-tables",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Import-Secret": secret,
        },
    )
    print(f"Descargando tablas desde Render ({len(wanted)} tablas) ...")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(
            f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"
        ) from exc

    tables_data = payload.get("tables") or {}
    # Semilla: copiar esquema desde la mejor base local (tablas vacías OK).
    schema_src = _pick_source(None)
    _copy_schema_and_data(schema_src, temp_db)

    conn = sqlite3.connect(temp_db.as_posix())
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        existing = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table, rows in tables_data.items():
            if table not in existing:
                print(f"  skip Render {table}: no hay tabla local de esquema")
                continue
            conn.execute(f'DELETE FROM "{table}"')
            if not rows:
                print(f"  {table}: 0 (Render)")
                continue
            cols = list(rows[0].keys())
            col_list = ", ".join(f'"{c}"' for c in cols)
            placeholders = ", ".join("?" for _ in cols)
            values = [tuple(r.get(c) for c in cols) for r in rows]
            conn.executemany(
                f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
                values,
            )
            print(f"  {table}: {len(values)} (Render)")
        conn.commit()
    finally:
        conn.close()
    return temp_db


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exporta paquete Capacitación (código + datos) sin tocar origen."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Ruta a gos.db fuente (default: la local con más filas cap_*).",
    )
    parser.add_argument(
        "--from-render",
        action="store_true",
        help="Rellena datos desde Render (solo lectura) sobre un SQLite temporal.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Carpeta destino (default: exports/capacitacion-TIMESTAMP).",
    )
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = (args.out or (EXPORTS_ROOT / f"capacitacion-{stamp}")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    temp_render: Path | None = None
    try:
        if args.from_render:
            temp_render = out_dir / "_tmp_render_source.db"
            source = _try_pull_render_to_temp(temp_render)
            source_label = f"Render (+ esquema local)"
        else:
            source = _pick_source(args.source)
            source_label = str(source.relative_to(ROOT) if source.is_relative_to(ROOT) else source)

        print(f"\n=== Export Capacitacion -> {out_dir} ===\n")
        print("1) Base de datos (solo copia)...")
        db_dest = out_dir / "datos" / "capacitacion.db"
        counts = _copy_schema_and_data(source, db_dest)

        print("\n2) Código del módulo...")
        code_files = _copy_module(out_dir / "codigo" / "capacitacion")
        print(f"  {code_files} archivos")

        print("\n3) Storage evidencias...")
        storage_files = _copy_storage(out_dir / "storage" / "capacitacion")
        print(f"  {storage_files} archivos")

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": source_label,
            "source_path": str(source),
            "from_render": bool(args.from_render),
            "module_files": code_files,
            "storage_files": storage_files,
            "table_counts": counts,
            "cap_rows_total": sum(v for k, v in counts.items() if k.startswith("cap_")),
            "note": "Copia de solo lectura. Origen GOS no modificado.",
        }
        (out_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _write_readme(
            out_dir / "README.md",
            stamp=manifest["generated_at"],
            source=Path(source_label),
            counts=counts,
        )

        if temp_render and temp_render.exists():
            temp_render.unlink()

        zip_path = out_dir.parent / f"{out_dir.name}.zip"
        print("\n4) ZIP...")
        _zip_dir(out_dir, zip_path)
        print(f"  {zip_path}")

        # Verificación: origen intacto (solo advertencia si no es el temp)
        if not args.from_render:
            after = _cap_row_total(source)
            print(f"\nOrigen intacto: {source.name} sigue con {after} filas cap_*.")

        print("\nListo.")
        print(f"  Carpeta: {out_dir}")
        print(f"  ZIP:     {zip_path}")
        print(f"  Filas cap_*: {manifest['cap_rows_total']}")
        return 0
    except Exception:
        if temp_render and temp_render.exists():
            try:
                temp_render.unlink()
            except OSError:
                pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
