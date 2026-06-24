import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gos import create_app
from gos.extensions import db
from gos.models import Empresa, Usuario
from gos.modulos.objetivos.models import (  # noqa: F401 — registrar tablas
    Area,
    FodaDocumento,
    FodaItem,
    DafoTarea,
    Objetivo,
    PlaneamientoConfig,
    Responsable,
    Sector,
)
from gos.modulos.capacitacion.models import (  # noqa: F401
    Participante,
    Curso,
    Puesto,
)


def init_db():
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Tablas creadas (incluye FODA).")


if __name__ == "__main__":
    init_db()
