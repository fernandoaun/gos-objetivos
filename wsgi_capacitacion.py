"""WSGI Capacitación (programa separado)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ["GOS_APP_MODE"] = "capacitacion"
os.environ.setdefault(
    "GOS_DATABASE_PATH",
    str(ROOT / "instance" / "capacitacion" / "gos_cap.db"),
)

from gos import create_app

app = create_app()
