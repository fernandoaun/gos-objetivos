from gos.extensions import db
from gos.models import Usuario
from gos.models.usuario import ROLES

MIN_PASSWORD_LEN = 6


def listar_usuarios_empresa(empresa_id: int) -> list[Usuario]:
    return (
        Usuario.query.filter_by(empresa_id=empresa_id)
        .order_by(Usuario.nombre)
        .all()
    )


def crear_usuario(
    *,
    empresa_id: int,
    email: str,
    nombre: str,
    password: str,
    rol: str,
) -> tuple[Usuario | None, str | None]:
    email = email.strip().lower()
    nombre = nombre.strip()

    if not email or not nombre:
        return None, "Email y nombre son obligatorios."
    if rol not in ROLES:
        return None, "Rol inválido."
    if len(password) < MIN_PASSWORD_LEN:
        return None, f"La contraseña debe tener al menos {MIN_PASSWORD_LEN} caracteres."

    if Usuario.query.filter_by(email=email).first():
        return None, f"Ya existe un usuario con el email {email}."

    user = Usuario(empresa_id=empresa_id, email=email, nombre=nombre, rol=rol)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, None


def actualizar_usuario(
    user: Usuario,
    *,
    nombre: str,
    rol: str,
    activo: bool,
    password: str | None = None,
) -> str | None:
    nombre = nombre.strip()
    if not nombre:
        return "El nombre es obligatorio."
    if rol not in ROLES:
        return "Rol inválido."
    if password is not None and password != "":
        if len(password) < MIN_PASSWORD_LEN:
            return f"La contraseña debe tener al menos {MIN_PASSWORD_LEN} caracteres."
        user.set_password(password)

    user.nombre = nombre
    user.rol = rol
    user.activo = activo
    db.session.commit()
    return None
