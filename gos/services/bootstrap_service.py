from sqlalchemy.exc import IntegrityError

from gos import env
from gos.extensions import db
from gos.models import Empresa, Usuario
from gos.modulos.objetivos.models.catalogos import PlaneamientoConfig


def ensure_initial_admin() -> None:
    """Solo en producción: crea el admin si no existe."""
    if not env.is_production():
        return

    email = env.admin_email()
    password = env.admin_password()

    if Usuario.query.filter_by(email=email).first():
        return

    empresa = Empresa.query.filter_by(activa=True).first()
    if not empresa:
        empresa = Empresa(nombre=env.empresa_nombre(), activa=True)
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
        nombre=env.admin_nombre(),
        rol="administrador",
    )
    admin.set_password(password)
    db.session.add(admin)

    try:
        db.session.commit()
        print(f"[bootstrap] Usuario admin creado: {email}")
    except IntegrityError:
        db.session.rollback()
