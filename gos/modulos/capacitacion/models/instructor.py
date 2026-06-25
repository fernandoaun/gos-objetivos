from gos.extensions import db
from gos.models.base import TimestampMixin


class Instructor(db.Model, TimestampMixin):
    """Instructor interno o externo para cursos y encuentros."""

    __tablename__ = "cap_instructores"
    __table_args__ = (
        db.UniqueConstraint("empresa_id", "codigo", name="uq_cap_instructor_codigo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    telefono = db.Column(db.String(40), nullable=True)
    especialidad = db.Column(db.String(150), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    cursos = db.relationship("Curso", back_populates="instructor", lazy="dynamic")
