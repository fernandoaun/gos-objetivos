from datetime import datetime

from gos.extensions import db


class MantUnidad(db.Model):
    __tablename__ = "mant_unidades"
    __table_args__ = (db.UniqueConstraint("codigo", name="uq_mant_unidad_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(64), nullable=False)
    nombre = db.Column(db.String(128), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    celdas = db.relationship("MantPlanCelda", back_populates="unidad", cascade="all, delete-orphan")
    vtv = db.relationship("MantVtv", back_populates="unidad", uselist=False, cascade="all, delete-orphan")
    vtv_turnos = db.relationship(
        "MantVtvTurno", back_populates="unidad", cascade="all, delete-orphan"
    )


class MantPlanCelda(db.Model):
    """Celda mensual: R = referencia/tipo (1–4), P = programado, E = ejecutado."""

    __tablename__ = "mant_plan_celdas"
    __table_args__ = (
        db.UniqueConstraint("unidad_id", "anio", "mes", name="uq_mant_celda_unidad_anio_mes"),
    )

    id = db.Column(db.Integer, primary_key=True)
    unidad_id = db.Column(
        db.Integer, db.ForeignKey("mant_unidades.id", ondelete="CASCADE"), nullable=False
    )
    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)  # 1-12
    r = db.Column(db.Float, nullable=False, default=0)  # tipo de mantenimiento (1–4)
    p = db.Column(db.Float, nullable=False, default=0)  # 1 si se programó en este mes
    e = db.Column(db.Float, nullable=False, default=0)  # 1 si se ejecutó en este mes

    unidad = db.relationship("MantUnidad", back_populates="celdas")


class MantVtv(db.Model):
    """Estado actual de VTV por unidad (próximo vencimiento)."""

    __tablename__ = "mant_vtv"
    __table_args__ = (db.UniqueConstraint("unidad_id", name="uq_mant_vtv_unidad"),)

    id = db.Column(db.Integer, primary_key=True)
    unidad_id = db.Column(
        db.Integer, db.ForeignKey("mant_unidades.id", ondelete="CASCADE"), nullable=False
    )
    vencimiento = db.Column(db.Date, nullable=False)
    bloqueado = db.Column(db.Boolean, nullable=False, default=False)
    resultado_ultimo = db.Column(db.String(32))  # apto | condicional | rechazada
    observaciones = db.Column(db.Text)

    unidad = db.relationship("MantUnidad", back_populates="vtv")


class MantVtvTurno(db.Model):
    """Turno de VTV: solo martes y jueves. Baja del vehículo = fecha_vtv − 2 días."""

    __tablename__ = "mant_vtv_turnos"

    id = db.Column(db.Integer, primary_key=True)
    unidad_id = db.Column(
        db.Integer, db.ForeignKey("mant_unidades.id", ondelete="CASCADE"), nullable=False
    )
    fecha_vtv = db.Column(db.Date, nullable=False)
    fecha_baja = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(32), nullable=False, default="programada")
    # programada | realizada | cancelada
    resultado = db.Column(db.String(32))  # apto | condicional | rechazada
    fecha_realizada = db.Column(db.Date)
    certificado_path = db.Column(db.String(500))
    certificado_nombre = db.Column(db.String(255))
    observaciones = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    unidad = db.relationship("MantUnidad", back_populates="vtv_turnos")


class MantPlanMeta(db.Model):
    """Metadatos del plan anual importado (título, sector, observaciones)."""

    __tablename__ = "mant_plan_meta"
    __table_args__ = (db.UniqueConstraint("anio", name="uq_mant_plan_meta_anio"),)

    id = db.Column(db.Integer, primary_key=True)
    anio = db.Column(db.Integer, nullable=False)
    titulo = db.Column(db.String(255))
    sector = db.Column(db.String(128))
    observaciones = db.Column(db.Text)
