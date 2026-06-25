from gos.extensions import db
from gos.models.base import TimestampMixin

TIPOS_ALERTA = (
    "vencimiento",
    "pendiente_obligatorio",
    "curso_proximo",
    "evaluacion_pendiente",
    "certificacion_vencida",
)
NIVELES_ALERTA = ("info", "advertencia", "critico")


class AlertaCapacitacion(db.Model, TimestampMixin):
    """Alertas automáticas de vencimientos, pendientes y cursos próximos."""

    __tablename__ = "cap_alertas"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    participante_id = db.Column(db.Integer, db.ForeignKey("cap_participantes.id"), nullable=True, index=True)
    curso_id = db.Column(db.Integer, db.ForeignKey("cap_cursos.id"), nullable=True, index=True)
    encuentro_id = db.Column(db.Integer, db.ForeignKey("cap_encuentros.id"), nullable=True, index=True)
    tipo = db.Column(db.String(30), nullable=False)
    nivel = db.Column(db.String(15), default="advertencia", nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    mensaje = db.Column(db.Text, nullable=True)
    fecha_referencia = db.Column(db.Date, nullable=True)
    leida = db.Column(db.Boolean, default=False, nullable=False)
    resuelta = db.Column(db.Boolean, default=False, nullable=False)

    empresa = db.relationship("Empresa")
    participante = db.relationship("Participante")
    curso = db.relationship("Curso")
    encuentro = db.relationship("EncuentroCapacitacion")
