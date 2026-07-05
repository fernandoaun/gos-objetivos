from gos.extensions import db
from gos.models.base import TimestampMixin

ESTADOS_PROGRAMA = ("borrador", "programado", "en_curso", "finalizado", "cancelado")
ESTADOS_ENCUENTRO = ("programado", "realizado", "cancelado", "reprogramado", "planificado", "en_curso", "cerrado")
ESTADOS_INSCRIPCION = ("inscripto", "en_curso", "completado", "abandonado")
ALCANCES_PROGRAMA = ("general", "puesto", "persona")
TIPOS_PROGRAMA = ("interno", "externo")


class ProgramaCapacitacion(db.Model, TimestampMixin):
    """Programa curricular: agrupa planes con cursos y aplica a uno o más puestos."""

    __tablename__ = "cap_programas"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectores.id"), nullable=True, index=True)
    puesto_id = db.Column(db.Integer, db.ForeignKey("cap_puestos.id"), nullable=True, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=True, index=True)
    alcance = db.Column(db.String(20), default="general", nullable=False)
    tipo = db.Column(db.String(20), default="interno", nullable=False)
    codigo = db.Column(db.String(30), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)
    instructor = db.Column(db.String(150), nullable=True)
    empresa_capacitadora_id = db.Column(
        db.Integer, db.ForeignKey("cap_empresas_capacitadoras.id"), nullable=True, index=True
    )
    estado = db.Column(db.String(20), default="borrador", nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    empresa_capacitadora = db.relationship("EmpresaCapacitadora")
    sector = db.relationship("Sector")
    puesto = db.relationship("Puesto")
    curso = db.relationship("Curso")
    planes = db.relationship(
        "ProgramaPlan",
        back_populates="programa",
        lazy="dynamic",
        order_by="ProgramaPlan.orden",
        cascade="all, delete-orphan",
    )
    puestos_asignados = db.relationship(
        "ProgramaPuesto",
        back_populates="programa",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    encuentros = db.relationship(
        "EncuentroCapacitacion",
        back_populates="programa",
        lazy="dynamic",
        order_by="EncuentroCapacitacion.fecha",
    )
    inscripciones = db.relationship("InscripcionPrograma", back_populates="programa", lazy="dynamic")


class ProgramaPlan(db.Model, TimestampMixin):
    """Plan o bloque dentro de un programa (Seguridad, Técnico, Liderazgo, etc.)."""

    __tablename__ = "cap_programa_planes"

    id = db.Column(db.Integer, primary_key=True)
    programa_id = db.Column(db.Integer, db.ForeignKey("cap_programas.id"), nullable=False, index=True)
    nombre = db.Column(db.String(150), nullable=False)
    orden = db.Column(db.Integer, default=1, nullable=False)

    programa = db.relationship("ProgramaCapacitacion", back_populates="planes")
    cursos = db.relationship(
        "PlanCurso",
        back_populates="plan",
        lazy="dynamic",
        order_by="PlanCurso.orden",
        cascade="all, delete-orphan",
    )


class PlanCurso(db.Model, TimestampMixin):
    """Curso perteneciente a un plan de un programa."""

    __tablename__ = "cap_plan_cursos"
    __table_args__ = (db.UniqueConstraint("plan_id", "curso_id", name="uq_cap_plan_curso"),)

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("cap_programa_planes.id"), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=False, index=True)
    orden = db.Column(db.Integer, default=1, nullable=False)

    plan = db.relationship("ProgramaPlan", back_populates="cursos")
    curso = db.relationship("Curso")


class ProgramaPuesto(db.Model, TimestampMixin):
    """Puestos a los que aplica un programa."""

    __tablename__ = "cap_programa_puestos"
    __table_args__ = (db.UniqueConstraint("programa_id", "puesto_id", name="uq_cap_programa_puesto"),)

    id = db.Column(db.Integer, primary_key=True)
    programa_id = db.Column(db.Integer, db.ForeignKey("cap_programas.id"), nullable=False, index=True)
    puesto_id = db.Column(db.Integer, db.ForeignKey("cap_puestos.id"), nullable=False, index=True)

    programa = db.relationship("ProgramaCapacitacion", back_populates="puestos_asignados")
    puesto = db.relationship("Puesto")


class EncuentroCapacitacion(db.Model, TimestampMixin):
    """Cronograma: instancia programada de un curso (planificación y cierre)."""

    __tablename__ = "cap_encuentros"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    programa_id = db.Column(db.Integer, db.ForeignKey("cap_programas.id"), nullable=True, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("cap_programa_planes.id"), nullable=True, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=True, index=True)
    numero = db.Column(db.Integer, nullable=True)  # encuentro 1, 2, 3...
    titulo = db.Column(db.String(200), nullable=False)
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=True)
    hora_fin = db.Column(db.Time, nullable=True)
    fecha_inicio = db.Column(db.DateTime, nullable=True)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    lugar = db.Column(db.String(200), nullable=True)
    link_virtual = db.Column(db.String(500), nullable=True)
    instructor = db.Column(db.String(150), nullable=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey("cap_instructores.id"), nullable=True, index=True)
    origen = db.Column(db.String(30), nullable=True)
    empresa_capacitadora_id = db.Column(
        db.Integer, db.ForeignKey("cap_empresas_capacitadoras.id"), nullable=True, index=True
    )
    estado = db.Column(db.String(20), default="planificado", nullable=False)
    material_adjunto_url = db.Column(db.String(500), nullable=True)
    resultados_adjunto_url = db.Column(db.String(500), nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    empresa = db.relationship("Empresa")
    programa = db.relationship("ProgramaCapacitacion", back_populates="encuentros")
    plan = db.relationship("ProgramaPlan")
    curso = db.relationship("Curso", back_populates="encuentros")
    instructor_rel = db.relationship("Instructor", foreign_keys=[instructor_id])
    empresa_capacitadora = db.relationship("EmpresaCapacitadora")
    puestos_convocados = db.relationship(
        "CronogramaPuesto",
        back_populates="encuentro",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
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


class CronogramaPuesto(db.Model, TimestampMixin):
    """Puestos convocados a un cronograma/encuentro."""

    __tablename__ = "cap_cronograma_puestos"
    __table_args__ = (
        db.UniqueConstraint("encuentro_id", "puesto_id", name="uq_cap_cronograma_puesto"),
    )

    id = db.Column(db.Integer, primary_key=True)
    encuentro_id = db.Column(db.Integer, db.ForeignKey("cap_encuentros.id"), nullable=False, index=True)
    puesto_id = db.Column(db.Integer, db.ForeignKey("cap_puestos.id"), nullable=False, index=True)

    encuentro = db.relationship("EncuentroCapacitacion", back_populates="puestos_convocados")
    puesto = db.relationship("Puesto")


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
