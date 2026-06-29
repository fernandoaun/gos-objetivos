from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from gos.extensions import db
from gos.models.base import TimestampMixin

ROLES = ("administrador", "usuario", "cliente", "angel")

ROL_LABELS = {
    "administrador": "Administrador",
    "usuario": "Usuario (alumno)",
    "cliente": "Cliente",
    "angel": "Ángel",
}

# Compatibilidad con roles anteriores en bases ya desplegadas
ROL_ALIASES = {
    "administrador": frozenset({"administrador", "admin"}),
    "usuario": frozenset({"usuario"}),
    "cliente": frozenset({"cliente", "consulta"}),
    "angel": frozenset({"angel", "gerente", "responsable"}),
}


def usuario_cumple_rol(user, *roles: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return False
    if user.es_administrador():
        return True
    permitidos: set[str] = set()
    for rol in roles:
        permitidos.update(ROL_ALIASES.get(rol, {rol}))
    return user.rol in permitidos


class Usuario(UserMixin, db.Model, TimestampMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(30), default="administrador", nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    perfil_id = db.Column(db.Integer, db.ForeignKey("perfiles.id"), nullable=True, index=True)

    empresa = db.relationship("Empresa", back_populates="usuarios")
    perfil = db.relationship("Perfil", back_populates="usuarios")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def es_administrador(self) -> bool:
        return self.rol in ROL_ALIASES["administrador"]

    def es_angel(self) -> bool:
        return self.rol in ROL_ALIASES["angel"]

    def es_cliente(self) -> bool:
        return self.rol in ROL_ALIASES["cliente"]

    def es_usuario(self) -> bool:
        return self.rol in ROL_ALIASES["usuario"]

    def puede_configurar(self) -> bool:
        return self.es_administrador() or self.es_angel()

    def puede_editar_operativa(self) -> bool:
        return self.es_administrador() or self.es_angel()

    def es_solo_lectura(self) -> bool:
        return self.es_cliente()

    def etiqueta_rol(self) -> str:
        if self.rol in ROL_LABELS:
            return ROL_LABELS[self.rol]
        legacy = {
            "admin": ROL_LABELS["administrador"],
            "gerente": ROL_LABELS["angel"],
            "responsable": ROL_LABELS["angel"],
            "consulta": ROL_LABELS["cliente"],
        }
        return legacy.get(self.rol, self.rol)
