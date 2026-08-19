from gos.extensions import db
from gos.models.base import TimestampMixin


class ClienteCapacitacion(db.Model, TimestampMixin):
    """Empresa cliente a la que se puede afectar personal (informes por cliente)."""

    __tablename__ = "cap_clientes"
    __table_args__ = (db.UniqueConstraint("empresa_id", "codigo", name="uq_cap_cliente_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    logo_path = db.Column(db.String(500), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    empresa = db.relationship("Empresa")
    asignaciones = db.relationship(
        "ParticipanteCliente",
        back_populates="cliente",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class ParticipanteCliente(db.Model, TimestampMixin):
    """Vínculo N:N: una persona puede estar afectada a varios clientes."""

    __tablename__ = "cap_participante_clientes"
    __table_args__ = (
        db.UniqueConstraint("participante_id", "cliente_id", name="uq_cap_participante_cliente"),
    )

    id = db.Column(db.Integer, primary_key=True)
    participante_id = db.Column(
        db.Integer, db.ForeignKey("cap_participantes.id"), nullable=False, index=True
    )
    cliente_id = db.Column(db.Integer, db.ForeignKey("cap_clientes.id"), nullable=False, index=True)

    participante = db.relationship("Participante", back_populates="clientes")
    cliente = db.relationship("ClienteCapacitacion", back_populates="asignaciones")
