from pathlib import Path

from gos import env
from gos.config import BASE_DIR

DATA_DIR = env.ralenti_data_dir()
DB_PATH = env.ralenti_db_path()
LEGACY_DB_PATH = BASE_DIR.parent / "GOS Hs Ralenti" / "data" / "gos_ralenti.db"
