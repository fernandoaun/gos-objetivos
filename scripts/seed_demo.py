"""Carga datos demo. Uso: flask --app wsgi shell < scripts/seed_demo.py o python -m scripts.seed_demo"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app
from app.extensions import db
from app.models import Area, Empresa, PlaneamientoConfig, Responsable, Sector, Usuario


def seed():
    app = create_app()
    with app.app_context():
        if Usuario.query.filter_by(email="admin@demo.local").first():
            print("Demo ya cargada.")
            return

        empresa = Empresa(nombre="Empresa Demo S.A.")
        db.session.add(empresa)
        db.session.flush()

        db.session.add(
            PlaneamientoConfig(empresa_id=empresa.id, umbral_verde=90, umbral_amarillo=70)
        )

        s1 = Sector(empresa_id=empresa.id, codigo="COM", nombre="Comercial")
        s2 = Sector(empresa_id=empresa.id, codigo="OPE", nombre="Operaciones")
        db.session.add_all([s1, s2])
        db.session.flush()

        a1 = Area(empresa_id=empresa.id, codigo="VEN", nombre="Ventas", sector_id=s1.id)
        a2 = Area(empresa_id=empresa.id, codigo="LOG", nombre="Logística", sector_id=s2.id)
        db.session.add_all([a1, a2])
        db.session.flush()

        db.session.add(
            Responsable(
                empresa_id=empresa.id,
                codigo="R-001",
                nombre="María González",
                email="maria@demo.local",
                area_id=a1.id,
            )
        )

        admin = Usuario(
            empresa_id=empresa.id,
            email="admin@demo.local",
            nombre="Administrador Demo",
            rol="admin",
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("Demo OK: admin@demo.local / admin123")


if __name__ == "__main__":
    seed()
