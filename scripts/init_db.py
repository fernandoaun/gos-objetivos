import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app
from app.extensions import db
from app.models import (  # noqa: F401 — registrar tablas
    Area,
    Empresa,
    FodaDocumento,
    FodaItem,
    DafoTarea,
    Objetivo,
    PlaneamientoConfig,
    Responsable,
    Sector,
    Usuario,
)


def init_db():
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Tablas creadas (incluye FODA).")


if __name__ == "__main__":
    init_db()
