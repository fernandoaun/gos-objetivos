"""Renumera ítems FODA activos para que empiecen en F-001, O-001, etc."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gos import create_app
from gos.extensions import db
from gos.models import Empresa
from gos.modulos.objetivos.services.foda_service import renumerar_codigos_activos


def main():
    app = create_app()
    with app.app_context():
        for emp in Empresa.query.all():
            renumerar_codigos_activos(emp.id)
            print(f"Empresa {emp.nombre}: códigos renumerados desde 001")
        db.session.commit()
        print("Listo.")


if __name__ == "__main__":
    main()
