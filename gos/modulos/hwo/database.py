from pathlib import Path

from gos import env
from gos.config import BASE_DIR

DATA_DIR = env.hwo_data_dir()
DB_PATH = env.hwo_db_path()
LEGACY_DATA_DIR = BASE_DIR.parent / "Analisis HWO" / "data"
