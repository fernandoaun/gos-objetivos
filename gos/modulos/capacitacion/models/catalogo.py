from gos.extensions import db
from gos.models.base import TimestampMixin
from gos.modulos.capacitacion.models.taxonomia import MODALIDADES, TIPOS_CAPACITACION  # noqa: F401


class Centro(db.Model, TimestampMixin):
    """Catálogo de centros de trabajo."""

    __tablename__ = "cap_centros"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_cap_centro_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    participantes = db.relationship("Participante", back_populates="centro", lazy="dynamic")


class Puesto(db.Model, TimestampMixin):
    """Catálogo de puestos/cargos para requisitos y filtros."""

    __tablename__ = "cap_puestos"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_cap_puesto_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectores.id"), nullable=True, index=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    sector = db.relationship("Sector")
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
    categoria = db.Column(db.String(30), nullable=True)
    tipo = db.Column(db.String(30), nullable=True)
    origen = db.Column(db.String(30), nullable=True)
    tipo_capacitacion = db.Column(db.String(30), nullable=True)  # legado / reportes ISO
    horas = db.Column(db.Numeric(6, 2), nullable=True)
    modalidad = db.Column(db.String(30), nullable=True)
    temas = db.Column(db.Text, nullable=True)
    vigencia_meses = db.Column(db.Integer, nullable=True)  # validez del conocimiento
    requiere_evaluacion = db.Column(db.Boolean, default=False, nullable=False)
    puntaje_minimo = db.Column(db.Numeric(5, 2), nullable=True)

    @property
    def tiene_vigencia(self) -> bool:
        return bool(self.vigencia_meses and self.vigencia_meses > 0)

    @property
    def duracion_horas(self):
        return float(self.horas) if self.horas is not None else None
    instructor_id = db.Column(db.Integer, db.ForeignKey("cap_instructores.id"), nullable=True, index=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    instructor = db.relationship("Instructor", back_populates="cursos")
    encuentros = db.relationship("EncuentroCapacitacion", back_populates="curso", lazy="dynamic")
    registros = db.relationship("RegistroCapacitacion", back_populates="curso", lazy="dynamic")
    requisitos = db.relationship("RequisitoFormacion", back_populates="curso", lazy="dynamic")
    planes = db.relationship("PlanCapacitacion", back_populates="curso", lazy="dynamic")


class EmpresaCapacitadora(db.Model, TimestampMixin):
    """Proveedor externo que dicta capacitaciones."""

    __tablename__ = "cap_empresas_capacitadoras"
    __table_args__ = (
        db.UniqueConstraint("empresa_id", "codigo", name="uq_cap_emp_cap_codigo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    contacto = db.Column(db.String(150), nullable=True)
    telefono = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")


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
