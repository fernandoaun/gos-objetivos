from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from gos.extensions import db
from gos.models.base import TimestampMixin

ROLES = ("admin", "gerente", "responsable", "consulta")


class Usuario(UserMixin, db.Model, TimestampMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(30), default="admin", nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa", back_populates="usuarios")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def puede_configurar(self) -> bool:
        return self.rol in ("admin", "gerente")
