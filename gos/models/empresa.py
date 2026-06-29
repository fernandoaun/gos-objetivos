from gos.extensions import db
from gos.models.base import TimestampMixin


class Empresa(db.Model, TimestampMixin):
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    activa = db.Column(db.Boolean, default=True, nullable=False)

    usuarios = db.relationship("Usuario", back_populates="empresa", lazy="dynamic")
    perfiles = db.relationship("Perfil", back_populates="empresa", lazy="dynamic")

    def __repr__(self):
        return f"<Empresa {self.nombre}>"
