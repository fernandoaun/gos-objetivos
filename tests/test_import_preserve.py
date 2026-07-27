"""Tests de importación segura (no wipe de tablas protegidas)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, text


def _make_sqlite(path: Path, *, perfiles: int = 0, participantes: int = 0) -> None:
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
    conn.execute(
        "INSERT INTO mant_unidades (id, codigo, nombre, activo) VALUES (1, 'U1', 'Unidad 1', 1)"
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


def test_import_tables_incluye_cap_y_perfiles():
    from gos.modulos.objetivos.services.import_service import PROTECTED_TABLES, TABLES

    assert "perfiles" in TABLES
    assert "cap_participantes" in TABLES
    assert "om_modules" in TABLES
    assert "perfiles" in PROTECTED_TABLES
    assert "cap_participantes" in PROTECTED_TABLES
    assert "objetivos" in PROTECTED_TABLES
    assert "foda_items" in PROTECTED_TABLES
