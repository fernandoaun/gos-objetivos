from datetime import date

from gos.extensions import db
from gos.models.base import TimestampMixin

OBJETIVO_ESTADOS = ("borrador", "activo", "en_revision", "finalizado")
OBJETIVO_ESTADO_LABELS = {
    "borrador": "Borrador",
    "activo": "Activo",
    "en_revision": "En revisión",
    "finalizado": "Finalizado",
}


class Objetivo(db.Model, TimestampMixin):
    __tablename__ = "objetivos"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_objetivo_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(30), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    responsable_texto = db.Column(db.String(250), nullable=True)
    responsable_id = db.Column(db.Integer, db.ForeignKey("responsables.id"), nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)
    estado = db.Column(db.String(20), default="activo", nullable=False)
    origen = db.Column(db.String(20), default="manual")
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    responsable = db.relationship("Responsable")
