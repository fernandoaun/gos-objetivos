from gos.extensions import db
from gos.models.base import TimestampMixin


class Puesto(db.Model, TimestampMixin):
    """Catálogo de puestos/cargos para requisitos y filtros."""

    __tablename__ = "cap_puestos"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_cap_puesto_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    participantes = db.relationship("Participante", back_populates="puesto", lazy="dynamic")
    requisitos = db.relationship("RequisitoFormacion", back_populates="puesto", lazy="dynamic")


class Curso(db.Model, TimestampMixin):
    """Definición de un curso o módulo de capacitación."""

    __tablename__ = "cap_cursos"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_cap_curso_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(30), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    horas = db.Column(db.Numeric(6, 2), nullable=True)
    modalidad = db.Column(db.String(30), nullable=True)  # presencial, virtual, mixta
    vigencia_meses = db.Column(db.Integer, nullable=True)  # validez del conocimiento
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    encuentros = db.relationship("EncuentroCapacitacion", back_populates="curso", lazy="dynamic")
    registros = db.relationship("RegistroCapacitacion", back_populates="curso", lazy="dynamic")
    requisitos = db.relationship("RequisitoFormacion", back_populates="curso", lazy="dynamic")
    planes = db.relationship("PlanCapacitacion", back_populates="curso", lazy="dynamic")


class CertificacionTipo(db.Model, TimestampMixin):
    """Tipos de certificación (ISO, seguridad, operativa, etc.)."""

    __tablename__ = "cap_certificacion_tipos"
    __table_args__ = (
        db.UniqueConstraint("empresa_id", "codigo", name="uq_cap_cert_tipo_codigo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(30), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    organismo_emisor = db.Column(db.String(150), nullable=True)
    vigencia_meses = db.Column(db.Integer, nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    certificaciones = db.relationship("CertificacionEmpleado", back_populates="tipo", lazy="dynamic")
    requisitos = db.relationship("RequisitoFormacion", back_populates="certificacion_tipo", lazy="dynamic")
