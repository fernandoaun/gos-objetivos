from gos.extensions import db
from gos.models.base import TimestampMixin


class Sector(db.Model, TimestampMixin):
    __tablename__ = "sectores"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_sector_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    areas = db.relationship("Area", back_populates="sector", lazy="dynamic")


class Area(db.Model, TimestampMixin):
    __tablename__ = "areas"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_area_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectores.id"), nullable=True)
    codigo = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    empresa = db.relationship("Empresa")
    sector = db.relationship("Sector", back_populates="areas")
    responsables = db.relationship("Responsable", back_populates="area", lazy="dynamic")


class Responsable(db.Model, TimestampMixin):
    __tablename__ = "responsables"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_responsable_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    area_id = db.Column(db.Integer, db.ForeignKey("areas.id"), nullable=True)
    codigo = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    area = db.relationship("Area", back_populates="responsables")


class PlaneamientoConfig(db.Model, TimestampMixin):
    __tablename__ = "planeamiento_config"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), unique=True, nullable=False)
    umbral_verde = db.Column(db.Numeric(5, 2), default=90, nullable=False)
    umbral_amarillo = db.Column(db.Numeric(5, 2), default=70, nullable=False)
    periodo_seguimiento_default = db.Column(db.String(20), default="mensual", nullable=False)
    auto_plan_accion = db.Column(db.Boolean, default=True, nullable=False)
    openai_model_override = db.Column(db.String(50), nullable=True)

    empresa = db.relationship("Empresa")
