from gos.extensions import db
from gos.models import Empresa, Usuario

DEFAULT_EMAIL = "admin@gos.local"
DEFAULT_NOMBRE = "Usuario GOS"
DEFAULT_EMPRESA = "GOS"


def obtener_o_crear_usuario_default() -> Usuario:
    user = Usuario.query.filter_by(email=DEFAULT_EMAIL, activo=True).first()
    if user:
        return user

    user = Usuario.query.filter_by(activo=True).first()
    if user:
        return user

    empresa = Empresa.query.filter_by(activa=True).first()
    if not empresa:
        empresa = Empresa(nombre=DEFAULT_EMPRESA, activa=True)
        db.session.add(empresa)
        db.session.flush()

    user = Usuario(
        empresa_id=empresa.id,
        email=DEFAULT_EMAIL,
        nombre=DEFAULT_NOMBRE,
        rol="administrador",
    )
    user.set_password("gos")
    db.session.add(user)
    db.session.commit()
    return user
