"""Legajo opcional para organigrama SGC (tabla propia sgi_*; no toca Personal/Vacaciones)."""

from __future__ import annotations

from gos.extensions import db


class EmpleadoPersonal(db.Model):
    """Stub mínimo compatible con organigrama / difusión del SGC QDV."""

    __tablename__ = "sgi_empleados_personal"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    puesto = db.Column(db.String(256), nullable=False, default="", server_default="")
    email = db.Column(db.String(256), nullable=False, default="", server_default="")
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default="1")

    user = db.relationship("Usuario", foreign_keys=[user_id])
