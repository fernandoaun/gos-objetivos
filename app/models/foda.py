from datetime import date

from app.extensions import db
from app.models.base import TimestampMixin

FODA_TIPOS = ("F", "O", "D", "A")
FODA_LABELS = {
    "F": "Fortalezas",
    "O": "Oportunidades",
    "D": "Debilidades",
    "A": "Amenazas",
}


class FodaDocumento(db.Model, TimestampMixin):
    """Registro de cada importación desde Word."""

    __tablename__ = "foda_documentos"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    ruta_archivo = db.Column(db.String(500), nullable=True)
    total_items = db.Column(db.Integer, default=0)
    subido_por = db.Column(db.String(150), nullable=True)

    items = db.relationship("FodaItem", back_populates="documento", lazy="dynamic")


class FodaItem(db.Model, TimestampMixin):
    __tablename__ = "foda_items"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_foda_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    documento_id = db.Column(db.Integer, db.ForeignKey("foda_documentos.id"), nullable=True)
    tipo = db.Column(db.String(1), nullable=False)
    codigo = db.Column(db.String(30), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey("areas.id"), nullable=True)
    responsable_id = db.Column(db.Integer, db.ForeignKey("responsables.id"), nullable=True)
    fecha = db.Column(db.Date, default=date.today)
    orden = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    origen = db.Column(db.String(20), default="word")

    documento = db.relationship("FodaDocumento", back_populates="items")
    area = db.relationship("Area")
    responsable = db.relationship("Responsable")


class DafoTarea(db.Model, TimestampMixin):
    """Una tarea editable por cuadrante de la matriz DAFO (FO, FA, DO o DA)."""

    __tablename__ = "dafo_tareas"
    __table_args__ = (
        db.UniqueConstraint(
            "empresa_id",
            "tipo",
            "origen_a_codigo",
            "origen_b_codigo",
            name="uq_dafo_celda",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    tipo = db.Column(db.String(2), nullable=False)
    origen_a_codigo = db.Column(db.String(30), nullable=False)
    origen_b_codigo = db.Column(db.String(30), nullable=False)
    tarea = db.Column(db.Text, nullable=False)
