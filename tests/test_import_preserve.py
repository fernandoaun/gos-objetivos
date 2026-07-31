"""Tests de importación segura (no wipe entre módulos)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, text


def _make_sqlite(
    path: Path,
    *,
    perfiles: int = 0,
    participantes: int = 0,
    mant_unidades: int = 1,
    vacaciones: int = 0,
    ralenti_files: int = 0,
) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE empresas (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE perfiles (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            modulos TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            nombre TEXT NOT NULL,
            password_hash TEXT,
            rol TEXT,
            activo INTEGER DEFAULT 1,
            perfil_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE cap_participantes (
            id INTEGER PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            apellido TEXT,
            legajo TEXT,
            email TEXT,
            activo INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE mant_unidades (
            id INTEGER PRIMARY KEY,
            codigo TEXT NOT NULL,
            nombre TEXT NOT NULL,
            activo INTEGER DEFAULT 1
        );
        CREATE TABLE vacaciones (
            id INTEGER PRIMARY KEY,
            registro_id INTEGER,
            anio INTEGER,
            dias REAL
        );
        CREATE TABLE ralenti_files (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            imported_at TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO empresas (id, nombre) VALUES (1, 'GOS')"
    )
    conn.execute(
        "INSERT INTO usuarios (id, empresa_id, email, nombre, rol, activo) "
        "VALUES (1, 1, 'admin@gos.local', 'Admin', 'administrador', 1)"
    )
    for i in range(perfiles):
        conn.execute(
            "INSERT INTO perfiles (id, empresa_id, nombre, modulos) VALUES (?, 1, ?, ?)",
            (i + 1, f"P{i+1}", '["objetivos"]'),
        )
    for i in range(participantes):
        conn.execute(
            "INSERT INTO cap_participantes (id, empresa_id, nombre, legajo, activo) "
            "VALUES (?, 1, ?, ?, 1)",
            (i + 1, f"Persona {i+1}", f"L{i+1}"),
        )
    for i in range(mant_unidades):
        conn.execute(
            "INSERT INTO mant_unidades (id, codigo, nombre, activo) VALUES (?, ?, ?, 1)",
            (i + 1, f"U{i+1}", f"Unidad {i+1}"),
        )
    for i in range(vacaciones):
        conn.execute(
            "INSERT INTO vacaciones (id, registro_id, anio, dias) VALUES (?, 1, ?, 10)",
            (i + 1, 2024 + i),
        )
    for i in range(ralenti_files):
        conn.execute(
            "INSERT INTO ralenti_files (id, nombre) VALUES (?, ?)",
            (i + 1, f"file{i+1}.csv"),
        )
    conn.commit()
    conn.close()


def test_import_preserves_protected_when_source_empty(tmp_path: Path):
    from gos.modulos.objetivos.services.import_service import importar_sqlite

    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    # Origen: sin perfiles ni personas (como el backup local vacío de cap)
    _make_sqlite(source, perfiles=0, participantes=0)
    # Destino: sí tiene datos protegidos
    _make_sqlite(target, perfiles=3, participantes=5)

    result = importar_sqlite(source, f"sqlite:///{target.as_posix()}")

    eng = create_engine(f"sqlite:///{target.as_posix()}")
    with eng.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM perfiles")).scalar() == 3
        assert conn.execute(text("SELECT COUNT(*) FROM cap_participantes")).scalar() == 5
        assert conn.execute(text("SELECT COUNT(*) FROM mant_unidades")).scalar() == 1
    assert result["mant_unidades"] == 1


def test_import_preserves_other_modules_when_only_mant_updated(tmp_path: Path):
    """Subir solo mant (VTV) no debe borrar vacaciones ni ralentí del destino."""
    from gos.modulos.objetivos.services.import_service import importar_sqlite

    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    _make_sqlite(source, mant_unidades=2, vacaciones=0, ralenti_files=0)
    _make_sqlite(target, mant_unidades=1, vacaciones=4, ralenti_files=3)

    importar_sqlite(source, f"sqlite:///{target.as_posix()}")

    eng = create_engine(f"sqlite:///{target.as_posix()}")
    with eng.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM mant_unidades")).scalar() == 2
        assert conn.execute(text("SELECT COUNT(*) FROM vacaciones")).scalar() == 4
        assert conn.execute(text("SELECT COUNT(*) FROM ralenti_files")).scalar() == 3


def test_import_preserves_mant_when_source_has_fewer_rows(tmp_path: Path):
    from gos.modulos.objetivos.services.import_service import importar_sqlite

    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    _make_sqlite(source, mant_unidades=1)
    _make_sqlite(target, mant_unidades=5)

    importar_sqlite(source, f"sqlite:///{target.as_posix()}")

    eng = create_engine(f"sqlite:///{target.as_posix()}")
    with eng.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM mant_unidades")).scalar() == 5


def test_import_tables_json_preserves_empty_payload(tmp_path: Path):
    from gos.modulos.objetivos.services.import_service import importar_tablas_json

    target = tmp_path / "target.db"
    _make_sqlite(target, vacaciones=3)

    result = importar_tablas_json(
        {"vacaciones": []},
        f"sqlite:///{target.as_posix()}",
    )

    eng = create_engine(f"sqlite:///{target.as_posix()}")
    with eng.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM vacaciones")).scalar() == 3
    assert result["vacaciones"] == 3


def test_import_tables_incluye_todos_los_modulos():
    from gos.modulos.objetivos.services.import_service import PROTECTED_TABLES, TABLES

    assert PROTECTED_TABLES == frozenset(TABLES)
    for table in (
        "perfiles",
        "cap_participantes",
        "om_modules",
        "objetivos",
        "foda_items",
        "mant_vtv",
        "mant_unidades",
        "hwo_datasets",
        "vacaciones",
        "tot_hs",
        "ralenti_files",
        "ralenti_events",
    ):
        assert table in PROTECTED_TABLES
