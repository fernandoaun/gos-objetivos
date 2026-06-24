from gos.extensions import db
from gos.models.base import TimestampMixin

ESTADOS_PLAN = ("pendiente", "programado", "completado", "cancelado")
RESULTADOS_ASISTENCIA = ("presente", "ausente", "justificado")


class RequisitoFormacion(db.Model, TimestampMixin):
    """
    Curso o certificación requerida según puesto, sector o persona específica.
    Solo uno de puesto_id / sector_id / participante_id debe estar definido (o combinación lógica).
    """

    __tablename__ = "cap_requisitos"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    puesto_id = db.Column(db.Integer, db.ForeignKey("cap_puestos.id"), nullable=True, index=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectores.id"), nullable=True, index=True)
    participante_id = db.Column(db.Integer, db.ForeignKey("cap_participantes.id"), nullable=True, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=True, index=True)
    certificacion_tipo_id = db.Column(
        db.Integer, db.ForeignKey("cap_certificacion_tipos.id"), nullable=True, index=True
    )
    obligatorio = db.Column(db.Boolean, default=True, nullable=False)
    observaciones = db.Column(db.Text, nullable=True)

    empresa = db.relationship("Empresa")
    puesto = db.relationship("Puesto", back_populates="requisitos")
    sector = db.relationship("Sector")
    participante = db.relationship("Participante", back_populates="requisitos")
    curso = db.relationship("Curso", back_populates="requisitos")
    certificacion_tipo = db.relationship("CertificacionTipo", back_populates="requisitos")


class AsistenciaEncuentro(db.Model, TimestampMixin):
    """Asistencia, nota y observaciones por participante en cada encuentro."""

    __tablename__ = "cap_asistencias"
    __table_args__ = (
        db.UniqueConstraint("encuentro_id", "participante_id", name="uq_cap_asistencia"),
    )

    id = db.Column(db.Integer, primary_key=True)
    encuentro_id = db.Column(db.Integer, db.ForeignKey("cap_encuentros.id"), nullable=False, index=True)
    participante_id = db.Column(db.Integer, db.ForeignKey("cap_participantes.id"), nullable=False, index=True)
    asistencia = db.Column(db.String(20), default="presente", nullable=False)
    nota = db.Column(db.Numeric(5, 2), nullable=True)
    aprobado = db.Column(db.Boolean, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    encuentro = db.relationship("EncuentroCapacitacion", back_populates="asistencias")
    participante = db.relationship("Participante", back_populates="asistencias")


class RegistroCapacitacion(db.Model, TimestampMixin):
    """Historial de curso completado por una persona."""

    __tablename__ = "cap_registros"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    participante_id = db.Column(db.Integer, db.ForeignKey("cap_participantes.id"), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=False, index=True)
    programa_id = db.Column(db.Integer, db.ForeignKey("cap_programas.id"), nullable=True, index=True)
    fecha_realizacion = db.Column(db.Date, nullable=False, index=True)
    nota = db.Column(db.Numeric(5, 2), nullable=True)
    aprobado = db.Column(db.Boolean, default=True, nullable=False)
    horas = db.Column(db.Numeric(6, 2), nullable=True)
    certificado_path = db.Column(db.String(500), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    vigente_hasta = db.Column(db.Date, nullable=True)

    empresa = db.relationship("Empresa")
    participante = db.relationship("Participante", back_populates="registros")
    curso = db.relationship("Curso", back_populates="registros")
    programa = db.relationship("ProgramaCapacitacion")


class CertificacionEmpleado(db.Model, TimestampMixin):
    """Certificación emitida a una persona."""

    __tablename__ = "cap_certificaciones"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    participante_id = db.Column(db.Integer, db.ForeignKey("cap_participantes.id"), nullable=False, index=True)
    tipo_id = db.Column(db.Integer, db.ForeignKey("cap_certificacion_tipos.id"), nullable=False, index=True)
    numero = db.Column(db.String(80), nullable=True)
    fecha_emision = db.Column(db.Date, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=True, index=True)
    organismo = db.Column(db.String(150), nullable=True)
    documento_path = db.Column(db.String(500), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    vigente = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    participante = db.relationship("Participante", back_populates="certificaciones")
    tipo = db.relationship("CertificacionTipo", back_populates="certificaciones")


class PlanCapacitacion(db.Model, TimestampMixin):
    """Planificación de un curso pendiente: cuándo y en qué encuentro lo realizará."""

    __tablename__ = "cap_planes"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    participante_id = db.Column(db.Integer, db.ForeignKey("cap_participantes.id"), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=False, index=True)
    programa_id = db.Column(db.Integer, db.ForeignKey("cap_programas.id"), nullable=True, index=True)
    encuentro_id = db.Column(db.Integer, db.ForeignKey("cap_encuentros.id"), nullable=True, index=True)
    fecha_planificada = db.Column(db.Date, nullable=True, index=True)
    estado = db.Column(db.String(20), default="pendiente", nullable=False)
    prioridad = db.Column(db.Integer, default=1, nullable=False)
    observaciones = db.Column(db.Text, nullable=True)

    empresa = db.relationship("Empresa")
    participante = db.relationship("Participante", back_populates="planes")
    curso = db.relationship("Curso", back_populates="planes")
    programa = db.relationship("ProgramaCapacitacion")
    encuentro = db.relationship("EncuentroCapacitacion", back_populates="planes")
