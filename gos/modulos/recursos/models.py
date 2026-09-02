from datetime import datetime

from gos.extensions import db

TIPOS_UNIDAD = ("UL", "TR", "ST", "OT")
GRUPOS_DESTINO = ("servicio", "estructura", "estado")

TIPO_LABELS = {
    "UL": "Unidad liviana",
    "TR": "Tractor",
    "ST": "Semi tanque",
    "OT": "Orden de Trabajo",
}

GRUPO_LABELS = {
    "servicio": "Servicio",
    "estructura": "Estructura",
    "estado": "Estado de parque",
}


class RecDestino(db.Model):
    __tablename__ = "rec_destinos"
    __table_args__ = (db.UniqueConstraint("codigo", name="uq_rec_destino_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(80), nullable=False)
    nombre = db.Column(db.String(160), nullable=False)
    grupo = db.Column(db.String(16), nullable=False, default="servicio")
    equipo = db.Column(db.String(80))
    orden = db.Column(db.Integer, nullable=False, default=0)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    columna_excel = db.Column(db.String(8))

    cupos = db.relationship("RecCupo", back_populates="destino", cascade="all, delete-orphan")
    asignaciones = db.relationship("RecAsignacion", back_populates="destino")
    centro = db.relationship("RecCentro", back_populates="destino", uselist=False)


class RecCentro(db.Model):
    __tablename__ = "rec_centros"
    __table_args__ = (db.UniqueConstraint("codigo", name="uq_rec_centro_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(80), nullable=False)
    nombre = db.Column(db.String(160), nullable=False)
    destino_id = db.Column(
        db.Integer, db.ForeignKey("rec_destinos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    activo = db.Column(db.Boolean, nullable=False, default=True)
    notas = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    destino = db.relationship("RecDestino", back_populates="centro")


class RecUnidad(db.Model):
    __tablename__ = "rec_unidades"
    __table_args__ = (db.UniqueConstraint("codigo", name="uq_rec_unidad_codigo"),)

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(64), nullable=False)
    interno = db.Column(db.String(64), nullable=False)
    dominio = db.Column(db.String(32))
    tipo = db.Column(db.String(8), nullable=False, default="OT")
    contratista = db.Column(db.String(32))
    es_centro = db.Column(db.Boolean, nullable=False, default=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    notas = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    asignacion = db.relationship(
        "RecAsignacion",
        back_populates="unidad",
        uselist=False,
        cascade="all, delete-orphan",
    )


class RecCupo(db.Model):
    __tablename__ = "rec_cupos"
    __table_args__ = (
        db.UniqueConstraint("destino_id", "tipo", name="uq_rec_cupo_destino_tipo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    destino_id = db.Column(
        db.Integer, db.ForeignKey("rec_destinos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo = db.Column(db.String(8), nullable=False)
    necesarias = db.Column(db.Integer, nullable=False, default=0)

    destino = db.relationship("RecDestino", back_populates="cupos")


class RecAsignacion(db.Model):
    __tablename__ = "rec_asignaciones"
    __table_args__ = (db.UniqueConstraint("unidad_id", name="uq_rec_asignacion_unidad"),)

    id = db.Column(db.Integer, primary_key=True)
    unidad_id = db.Column(
        db.Integer, db.ForeignKey("rec_unidades.id", ondelete="CASCADE"), nullable=False, index=True
    )
    destino_id = db.Column(
        db.Integer, db.ForeignKey("rec_destinos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    updated_by = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    unidad = db.relationship("RecUnidad", back_populates="asignacion")
    destino = db.relationship("RecDestino", back_populates="asignaciones")


class RecCambio(db.Model):
    __tablename__ = "rec_cambios"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    accion = db.Column(db.String(32), nullable=False)
    entidad = db.Column(db.String(24), nullable=False)
    entidad_id = db.Column(db.Integer, nullable=True)
    resumen = db.Column(db.String(400), nullable=False)
