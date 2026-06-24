import os

from sqlalchemy.exc import IntegrityError

from gos.extensions import db
from gos.models import Empresa, Usuario

DEFAULT_ADMIN_EMAIL = "admin@demo.local"
DEFAULT_ADMIN_PASSWORD = "admin123"


def ensure_initial_admin() -> None:
    """Solo en producción: crea el admin si no existe."""
    if os.environ.get("FLASK_ENV") != "production":
        return

    email = os.environ.get("GOS_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip().lower()
    password = os.environ.get("GOS_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

    if Usuario.query.filter_by(email=email).first():
        return

    empresa = Empresa.query.filter_by(activa=True).first()
    if not empresa:
        empresa = Empresa(
            nombre=os.environ.get("GOS_EMPRESA_NOMBRE", "Empresa Demo S.A."),
            activa=True,
        )
        db.session.add(empresa)
        db.session.flush()

    admin = Usuario(
        empresa_id=empresa.id,
        email=email,
        nombre=os.environ.get("GOS_ADMIN_NOMBRE", "Administrador"),
        rol="admin",
    )
    admin.set_password(password)
    db.session.add(admin)

    try:
        db.session.commit()
        print(f"[bootstrap] Usuario admin creado: {email}")
    except IntegrityError:
        db.session.rollback()
