from gos.extensions import db
from gos.models.base import TimestampMixin


class CapacitacionConfig(db.Model, TimestampMixin):
    """Umbrales de alerta, notificaciones y parámetros por empresa."""

    __tablename__ = "cap_config"

    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False, unique=True, index=True)
    dias_proximo_vencer = db.Column(db.Integer, default=30, nullable=False)
    dias_encuentro_proximo = db.Column(db.Integer, default=7, nullable=False)
    pct_cumplimiento_minimo = db.Column(db.Integer, default=80, nullable=False)
    notif_email_activo = db.Column(db.Boolean, default=False, nullable=False)
    notif_vencimiento = db.Column(db.Boolean, default=True, nullable=False)
    notif_obligatorio = db.Column(db.Boolean, default=True, nullable=False)
    notif_curso_proximo = db.Column(db.Boolean, default=True, nullable=False)
    emails_destinatarios = db.Column(db.Text, nullable=True)
    emails_por_sector = db.Column(db.Text, nullable=True)
    emails_por_rol = db.Column(db.Text, nullable=True)
    ultimo_envio_notif = db.Column(db.DateTime, nullable=True)

    empresa = db.relationship("Empresa")
