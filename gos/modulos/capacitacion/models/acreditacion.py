from gos.extensions import db
from gos.models.base import TimestampMixin


class Acreditacion(db.Model, TimestampMixin):
    """Cumplimiento de un curso dentro de un programa/plan para una persona."""

    __tablename__ = "cap_acreditaciones"
    __table_args__ = (
        db.UniqueConstraint(
            "persona_id",
            "programa_id",
            "plan_id",
            "curso_id",
            name="uq_cap_acreditacion",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    persona_id = db.Column(db.Integer, db.ForeignKey("cap_participantes.id"), nullable=False, index=True)
    programa_id = db.Column(db.Integer, db.ForeignKey("cap_programas.id"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("cap_programa_planes.id"), nullable=False, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=False, index=True)
    cronograma_persona_id = db.Column(
        db.Integer, db.ForeignKey("cap_asistencias.id"), nullable=True, index=True
    )
    aprobo = db.Column(db.Boolean, default=False, nullable=False)
    horas_acreditadas = db.Column(db.Numeric(6, 2), nullable=True)
    nota = db.Column(db.Numeric(5, 2), nullable=True)
    fecha_aprobacion = db.Column(db.Date, nullable=True)
    fecha_vencimiento = db.Column(db.Date, nullable=True, index=True)
    vigente = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    persona = db.relationship("Participante")
    programa = db.relationship("ProgramaCapacitacion")
    plan = db.relationship("ProgramaPlan")
    curso = db.relationship("Curso")
    cronograma_persona = db.relationship("AsistenciaEncuentro")
