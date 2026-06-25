from gos import env
from gos.extensions import db
from gos.models import Empresa, Usuario


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
