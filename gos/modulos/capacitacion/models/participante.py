from gos.extensions import db
from gos.models.base import TimestampMixin


class Participante(db.Model, TimestampMixin):
    """
    Persona sujeta a seguimiento de capacitación.
    Puede vincularse a un Responsable del módulo Objetivos o existir de forma independiente
    (p. ej. sincronizado desde Vacaciones por legajo).
    """

    __tablename__ = "cap_participantes"
    __table_args__ = (
        db.UniqueConstraint("empresa_id", "legajo", name="uq_cap_participante_legajo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    responsable_id = db.Column(db.Integer, db.ForeignKey("responsables.id"), nullable=True, index=True)
    sector_id = db.Column(db.Integer, db.ForeignKey("sectores.id"), nullable=True, index=True)
    puesto_id = db.Column(db.Integer, db.ForeignKey("cap_puestos.id"), nullable=True, index=True)
    legajo = db.Column(db.String(30), nullable=True)
    dni = db.Column(db.String(20), nullable=True)
    nombre = db.Column(db.String(150), nullable=False)
    apellido = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    telefono = db.Column(db.String(40), nullable=True)
    centro = db.Column(db.String(150), nullable=True)
    fecha_ingreso = db.Column(db.Date, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    foto_path = db.Column(db.String(500), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    responsable = db.relationship("Responsable")
    sector = db.relationship("Sector")
    puesto = db.relationship("Puesto", back_populates="participantes")
    inscripciones = db.relationship("InscripcionPrograma", back_populates="participante", lazy="dynamic")
    asistencias = db.relationship("AsistenciaEncuentro", back_populates="participante", lazy="dynamic")
    registros = db.relationship("RegistroCapacitacion", back_populates="participante", lazy="dynamic")
    certificaciones = db.relationship("CertificacionEmpleado", back_populates="participante", lazy="dynamic")
    planes = db.relationship("PlanCapacitacion", back_populates="participante", lazy="dynamic")
    requisitos = db.relationship("RequisitoFormacion", back_populates="participante", lazy="dynamic")

    @property
    def nombre_completo(self) -> str:
        if self.apellido:
            return f"{self.nombre} {self.apellido}".strip()
        return self.nombre
