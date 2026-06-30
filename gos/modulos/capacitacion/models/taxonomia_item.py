from gos.extensions import db
from gos.models.base import TimestampMixin

NIVELES_TAXONOMIA = ("categoria", "tipo", "origen", "modalidad")


class TaxonomiaItem(db.Model, TimestampMixin):
    """Ítem de la cascada Categoría → Tipo → Origen → Modalidad (por empresa)."""

    __tablename__ = "cap_taxonomia_items"
    __table_args__ = (
        db.UniqueConstraint(
            "empresa_id",
            "nivel",
            "parent_id",
            "codigo",
            name="uq_cap_taxonomia_item",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    nivel = db.Column(db.String(20), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("cap_taxonomia_items.id"), nullable=True, index=True)
    codigo = db.Column(db.String(30), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    orden = db.Column(db.Integer, default=0, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    parent = db.relationship("TaxonomiaItem", remote_side=[id], backref="hijos")
