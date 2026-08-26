"""Separa Capacitación y Objetivos en dos SQLite (Option B).

NO toca Render. NO borra la base origen: deja una copia de seguridad.

Produce:
  instance/capacitacion/gos_cap.db
      empresas, usuarios, perfiles, sectores, areas, responsables, cap_*
  instance/objetivos/gos.db
      todo lo demás (sin tablas cap_*), perfiles sin módulo capacitacion

Uso:
  python scripts/separar_bases_capacitacion.py
  python scripts/separar_bases_capacitacion.py --source instance/gos.db
  python scripts/separar_bases_capacitacion.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CAP_DIR = ROOT / "instance" / "capacitacion"
OBJ_DIR = ROOT / "instance" / "objetivos"
BACKUP_DIR = ROOT / "instance" / "backups"

# Identidad + catálogos que Cap necesita (y perfiles/usuarios).
IDENTITY_TABLES = (
    "empresas",
    "perfiles",
    "usuarios",
    "sectores",
    "areas",
    "responsables",
)


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
        raise SystemExit("ERROR: no hay gos.db local para separar.")
    scored.sort(key=lambda x: x[1], reverse=True)
    best, rows = scored[0]
    print(f"Fuente elegida: {best} ({rows} filas cap_*)")
    return best.resolve()


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _copy_tables(
    src: sqlite3.Connection,
    dest: sqlite3.Connection,
    tables: list[str],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    dest.execute("PRAGMA foreign_keys = OFF")
    for table in tables:
        row = src.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if not row or not row[0]:
            print(f"  skip {table}: sin DDL")
            continue
        ddl = row[0]
        # En Objetivos: quitar FK a cap_* de om_module_personnel si aparece.
        if table == "om_module_personnel":
            ddl = _strip_cap_fk_from_ddl(ddl)
        dest.execute(ddl)
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

        for idx_sql, in src.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND tbl_name=? AND sql IS NOT NULL",
            (table,),
        ):
            try:
                dest.execute(idx_sql)
            except sqlite3.Error as exc:
                print(f"  AVISO índice {table}: {exc}")

    seq = src.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
    ).fetchone()
    if seq:
        dest.execute(
            "CREATE TABLE IF NOT EXISTS sqlite_sequence(name TEXT, seq INTEGER)"
        )
        for name, val in src.execute(
            "SELECT name, seq FROM sqlite_sequence WHERE name IN (%s)"
            % (",".join("?" * len(tables))),
            tables,
        ):
            dest.execute(
                "INSERT OR REPLACE INTO sqlite_sequence(name, seq) VALUES (?, ?)",
                (name, val),
            )
    dest.commit()
    return counts


def _strip_cap_fk_from_ddl(ddl: str) -> str:
    """Elimina REFERENCES cap_* del CREATE TABLE (Option B)."""
    cleaned = re.sub(
        r",?\s*FOREIGN KEY\s*\(\s*participante_id\s*\)\s*REFERENCES\s+cap_participantes\s*\([^)]*\)(?:\s*ON\s+DELETE\s+\w+)?",
        "",
        ddl,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bparticipante_id\s+INTEGER\s+REFERENCES\s+cap_participantes\s*\([^)]*\)(?:\s*ON\s+DELETE\s+\w+)?",
        "participante_id INTEGER",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def _adjust_perfiles_cap(conn: sqlite3.Connection) -> int:
    """En Cap: dejar solo módulo capacitacion en JSON de perfiles."""
    updated = 0
    rows = conn.execute("SELECT id, modulos FROM perfiles").fetchall()
    for pid, raw in rows:
        mods = _parse_modulos(raw)
        if mods == ["capacitacion"]:
            continue
        new_mods = ["capacitacion"] if "capacitacion" in mods or not mods else ["capacitacion"]
        # Si el perfil no tenía Cap, igual le damos Cap (es la única app).
        conn.execute(
            "UPDATE perfiles SET modulos=? WHERE id=?",
            (json.dumps(new_mods, ensure_ascii=False), pid),
        )
        updated += 1
    conn.commit()
    return updated


def _adjust_perfiles_objetivos(conn: sqlite3.Connection) -> int:
    """En Objetivos: quitar capacitacion del JSON de perfiles."""
    updated = 0
    rows = conn.execute("SELECT id, modulos FROM perfiles").fetchall()
    for pid, raw in rows:
        mods = _parse_modulos(raw)
        if "capacitacion" not in mods:
            continue
        new_mods = [m for m in mods if m != "capacitacion"]
        if not new_mods:
            new_mods = ["dashboard"]
        conn.execute(
            "UPDATE perfiles SET modulos=? WHERE id=?",
            (json.dumps(new_mods, ensure_ascii=False), pid),
        )
        updated += 1
    conn.commit()
    return updated


def _parse_modulos(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
    else:
        data = raw
    if isinstance(data, list):
        return [str(x) for x in data]
    return []


def _clear_om_participante_links(conn: sqlite3.Connection) -> int:
    if "om_module_personnel" not in _table_names(conn):
        return 0
    cols = {r[1] for r in conn.execute('PRAGMA table_info("om_module_personnel")')}
    if "participante_id" not in cols:
        return 0
    cur = conn.execute(
        "UPDATE om_module_personnel SET participante_id=NULL "
        "WHERE participante_id IS NOT NULL"
    )
    conn.commit()
    return cur.rowcount


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Separa Cap y Objetivos en dos SQLite con perfiles clonados."
    )
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra qué haría, no escribe archivos.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribe instance/capacitacion y instance/objetivos si ya existen.",
    )
    args = parser.parse_args()

    source = _pick_source(args.source)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    cap_db = CAP_DIR / "gos_cap.db"
    obj_db = OBJ_DIR / "gos.db"

    print(f"Fuente: {source}")
    print(f"Cap -> {cap_db}")
    print(f"Obj -> {obj_db}")

    if args.dry_run:
        src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
        try:
            names = sorted(_table_names(src))
            caps = [n for n in names if n.startswith("cap_")]
            print(f"Tablas totales: {len(names)}")
            print(f"Tablas cap_*: {len(caps)}")
            for t in IDENTITY_TABLES:
                if t in names:
                    n = src.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                    print(f"  {t}: {n}")
            print("Dry-run OK (sin escribir).")
        finally:
            src.close()
        return 0

    if (cap_db.exists() or obj_db.exists()) and not args.force:
        raise SystemExit(
            "ERROR: ya existen bases separadas. Usá --force para sobrescribir "
            "o borrá instance/capacitacion e instance/objetivos."
        )

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"gos-antes-separacion-{stamp}.db"
    shutil.copy2(source, backup)
    print(f"Backup origen: {backup}")

    CAP_DIR.mkdir(parents=True, exist_ok=True)
    OBJ_DIR.mkdir(parents=True, exist_ok=True)

    cap_tmp = cap_db.with_suffix(".db.tmp")
    obj_tmp = obj_db.with_suffix(".db.tmp")
    for tmp in (cap_tmp, obj_tmp):
        if tmp.exists():
            tmp.unlink()

    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    try:
        existing = _table_names(src)
        caps = sorted(n for n in existing if n.startswith("cap_"))
        if not caps:
            raise SystemExit("ERROR: no hay tablas cap_* en la fuente.")

        parents = [t for t in IDENTITY_TABLES if t in existing]
        missing = [t for t in IDENTITY_TABLES if t not in existing]
        if missing:
            print(f"AVISO: tablas identidad ausentes: {', '.join(missing)}")

        print("\n=== Base Capacitación ===")
        dest_cap = sqlite3.connect(cap_tmp.as_posix())
        try:
            cap_counts = _copy_tables(src, dest_cap, parents + caps)
            n_perf = _adjust_perfiles_cap(dest_cap)
            print(f"Perfiles ajustados (solo Cap): {n_perf}")
        finally:
            dest_cap.close()

        print("\n=== Base Objetivos (sin cap_*) ===")
        obj_tables = sorted(n for n in existing if not n.startswith("cap_"))
        dest_obj = sqlite3.connect(obj_tmp.as_posix())
        try:
            obj_counts = _copy_tables(src, dest_obj, obj_tables)
            n_perf = _adjust_perfiles_objetivos(dest_obj)
            print(f"Perfiles ajustados (sin Cap): {n_perf}")
            cleared = _clear_om_participante_links(dest_obj)
            print(f"O&M participante_id limpiados: {cleared}")
        finally:
            dest_obj.close()
    finally:
        src.close()

    def _replace(tmp: Path, final: Path) -> Path:
        try:
            if final.exists():
                final.unlink()
            tmp.replace(final)
            return final
        except OSError as exc:
            print(
                f"AVISO: no se pudo reemplazar {final.name} ({exc}). "
                f"Quedó {tmp.name} — cerrá la app que la usa y renombrá."
            )
            return tmp

    cap_final = _replace(cap_tmp, cap_db)
    obj_final = _replace(obj_tmp, obj_db)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "backup": str(backup),
        "capacitacion_db": str(cap_final),
        "objetivos_db": str(obj_final),
        "cap_table_counts": cap_counts,
        "obj_table_count": len(obj_counts),
        "note": "Option B: dos programas, dos bases, perfiles clonados.",
    }
    (CAP_DIR / "SEPARACION.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (OBJ_DIR / "SEPARACION.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("\nListo.")
    print(f"  Cap:  {cap_final}")
    print(f"  Obj:  {obj_final}")
    print(f"  Backup intacto: {backup}")
    print("\nSiguiente:")
    print("  1) ABRIR CAPACITACION.bat  (puerto 5002)")
    print("  2) ABRIR GOS Objetivos.bat (modo objetivos, puerto 5001)")
    print("  Origen original NO se borró:", source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
