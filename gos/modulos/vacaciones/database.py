"""Rutas legacy del módulo Vacaciones (migración desde SQLite local)."""
from __future__ import annotations

from gos import env
from gos.config import BASE_DIR

DATA_DIR = env.vacaciones_db_path().parent
DB_PATH = env.vacaciones_db_path()
LEGACY_DB = BASE_DIR.parent / "LUZ GALLARDO" / "indicadores-app" / "data" / "indicadores.db"
