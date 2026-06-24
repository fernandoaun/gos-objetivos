from gos.extensions import db
from gos.models.base import TimestampMixin

ESTADOS_PROGRAMA = ("borrador", "programado", "en_curso", "finalizado", "cancelado")
ESTADOS_ENCUENTRO = ("programado", "realizado", "cancelado", "reprogramado")
ESTADOS_INSCRIPCION = ("inscripto", "en_curso", "completado", "abandonado")


class ProgramaCapacitacion(db.Model, TimestampMixin):
    """Programa o cohorte que agrupa encuentros (puede orientarse a un sector)."""

    __tablename__ = "cap_programas"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectores.id"), nullable=True, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=True, index=True)
    codigo = db.Column(db.String(30), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)
    instructor = db.Column(db.String(150), nullable=True)
    estado = db.Column(db.String(20), default="borrador", nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    sector = db.relationship("Sector")
    curso = db.relationship("Curso")
    encuentros = db.relationship(
        "EncuentroCapacitacion",
        back_populates="programa",
        lazy="dynamic",
        order_by="EncuentroCapacitacion.fecha",
    )
    inscripciones = db.relationship("InscripcionPrograma", back_populates="programa", lazy="dynamic")


class EncuentroCapacitacion(db.Model, TimestampMixin):
    """Encuentro o sesión con fecha, lugar e instructor."""

    __tablename__ = "cap_encuentros"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    programa_id = db.Column(db.Integer, db.ForeignKey("cap_programas.id"), nullable=True, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=True, index=True)
    numero = db.Column(db.Integer, nullable=True)  # encuentro 1, 2, 3...
    titulo = db.Column(db.String(200), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fin = db.Column(db.Time, nullable=True)
    lugar = db.Column(db.String(200), nullable=True)
    instructor = db.Column(db.String(150), nullable=True)
    estado = db.Column(db.String(20), default="programado", nullable=False)
    observaciones = db.Column(db.Text, nullable=True)

    empresa = db.relationship("Empresa")
    programa = db.relationship("ProgramaCapacitacion", back_populates="encuentros")
    curso = db.relationship("Curso", back_populates="encuentros")
    temas = db.relationship(
        "EncuentroTema",
        back_populates="encuentro",
        lazy="dynamic",
        order_by="EncuentroTema.orden",
    )
    asistencias = db.relationship("AsistenciaEncuentro", back_populates="encuentro", lazy="dynamic")
    planes = db.relationship("PlanCapacitacion", back_populates="encuentro", lazy="dynamic")


class EncuentroTema(db.Model, TimestampMixin):
    """Tema tratado en cada encuentro."""

    __tablename__ = "cap_encuentro_temas"

    id = db.Column(db.Integer, primary_key=True)
    encuentro_id = db.Column(db.Integer, db.ForeignKey("cap_encuentros.id"), nullable=False, index=True)
    orden = db.Column(db.Integer, default=1, nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    duracion_minutos = db.Column(db.Integer, nullable=True)

    encuentro = db.relationship("EncuentroCapacitacion", back_populates="temas")


class InscripcionPrograma(db.Model, TimestampMixin):
    """Inscripción de un participante a un programa."""

    __tablename__ = "cap_inscripciones"
    __table_args__ = (
        db.UniqueConstraint("programa_id", "participante_id", name="uq_cap_inscripcion"),
    )

    id = db.Column(db.Integer, primary_key=True)
    programa_id = db.Column(db.Integer, db.ForeignKey("cap_programas.id"), nullable=False, index=True)
    participante_id = db.Column(db.Integer, db.ForeignKey("cap_participantes.id"), nullable=False, index=True)
    fecha_inscripcion = db.Column(db.Date, nullable=True)
    estado = db.Column(db.String(20), default="inscripto", nullable=False)
    observaciones = db.Column(db.Text, nullable=True)

    programa = db.relationship("ProgramaCapacitacion", back_populates="inscripciones")
    participante = db.relationship("Participante", back_populates="inscripciones")
