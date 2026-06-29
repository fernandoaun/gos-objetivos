from gos.extensions import db
from gos.models.base import TimestampMixin


class Perfil(db.Model, TimestampMixin):
    __tablename__ = "perfiles"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    nombre = db.Column(db.String(100), nullable=False)
    modulos = db.Column(db.JSON, nullable=False, default=list)

    empresa = db.relationship("Empresa", back_populates="perfiles")
    usuarios = db.relationship("Usuario", back_populates="perfil")

    __table_args__ = (
        db.UniqueConstraint("empresa_id", "nombre", name="uq_perfil_empresa_nombre"),
    )

    def etiqueta_modulos(self, labels: dict[str, str]) -> str:
        if not self.modulos:
            return "Sin módulos"
        return ", ".join(labels.get(code, code) for code in self.modulos)

    def __repr__(self):
        return f"<Perfil {self.nombre}>"
