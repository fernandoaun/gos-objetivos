from gos import env
from gos.extensions import db
from gos.models import Empresa, Usuario
from gos.services.usuario_service import MIN_PASSWORD_LEN


def obtener_o_crear_usuario_default() -> Usuario:
    email = env.dev_login_email()
    user = Usuario.query.filter_by(email=email, activo=True).first()
    if user:
        return user

    user = Usuario.query.filter_by(activo=True).first()
    if user:
        return user

    empresa = Empresa.query.filter_by(activa=True).first()
    if not empresa:
        empresa = Empresa(nombre=env.dev_empresa_nombre(), activa=True)
        db.session.add(empresa)
        db.session.flush()

    user = Usuario(
        empresa_id=empresa.id,
        email=email,
        nombre=env.dev_login_nombre(),
        rol="administrador",
    )
    user.set_password(env.dev_login_password())
    db.session.add(user)
    db.session.commit()
    return user


def cambiar_contraseña(
    user: Usuario,
    *,
    actual: str,
    nueva: str,
    confirmacion: str,
) -> str | None:
    if not user.check_password(actual):
        return "La contraseña actual no es correcta."
    if len(nueva) < MIN_PASSWORD_LEN:
        return f"La nueva contraseña debe tener al menos {MIN_PASSWORD_LEN} caracteres."
    if nueva != confirmacion:
        return "La confirmación no coincide con la nueva contraseña."
    if user.check_password(nueva):
        return "La nueva contraseña debe ser distinta a la actual."

    user.set_password(nueva)
    db.session.commit()
    return None
