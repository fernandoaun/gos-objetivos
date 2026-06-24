import os

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Empresa, PlaneamientoConfig, Usuario

DEFAULT_ADMIN_EMAIL = "admin@demo.local"
DEFAULT_ADMIN_PASSWORD = "admin123"


def ensure_initial_admin() -> None:
    """Crea el usuario admin inicial si la base está vacía (p. ej. primer deploy en Render)."""
    email = os.environ.get("GOS_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip().lower()
    password = os.environ.get("GOS_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

    if Usuario.query.filter_by(email=email, activo=True).first():
        return

    empresa = Empresa.query.filter_by(activa=True).first()
    if not empresa:
        empresa = Empresa(
            nombre=os.environ.get("GOS_EMPRESA_NOMBRE", "Empresa Demo S.A."),
            activa=True,
        )
        db.session.add(empresa)
        db.session.flush()
        db.session.add(PlaneamientoConfig(empresa_id=empresa.id))

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
    except IntegrityError:
        db.session.rollback()
