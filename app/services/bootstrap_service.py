import os

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Empresa, PlaneamientoConfig, Usuario

DEFAULT_ADMIN_EMAIL = "admin@demo.local"
DEFAULT_ADMIN_PASSWORD = "admin123"


def ensure_initial_admin() -> None:
    """Crea o repara el usuario admin inicial (primer deploy o recuperación)."""
    email = os.environ.get("GOS_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).strip().lower()
    password = os.environ.get("GOS_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

    user = Usuario.query.filter_by(email=email).first()
    if user:
        changed = False
        if not user.activo:
            user.activo = True
            changed = True
        if not user.check_password(password):
            user.set_password(password)
            changed = True
        if changed:
            db.session.commit()
            print(f"[bootstrap] Usuario admin actualizado: {email}")
        return

    empresa = Empresa.query.filter_by(activa=True).first()
    if not empresa:
        empresa = Empresa(
            nombre=os.environ.get("GOS_EMPRESA_NOMBRE", "Empresa Demo S.A."),
            activa=True,
        )
        db.session.add(empresa)
        db.session.flush()
        db.session.add(
            PlaneamientoConfig(
                empresa_id=empresa.id,
                umbral_verde=90,
                umbral_amarillo=70,
            )
        )

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
        print(f"[bootstrap] Usuario admin ya existía (concurrencia): {email}")
