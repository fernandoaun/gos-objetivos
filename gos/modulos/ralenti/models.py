from gos.extensions import db


class RalentiFile(db.Model):
    __tablename__ = "ralenti_files"
    __table_args__ = (db.UniqueConstraint("name", name="uq_ralenti_file_name"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(512), nullable=False, index=True)
    imported_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    event_count = db.Column(db.Integer, nullable=False, default=0)
    persons = db.Column(db.Text, nullable=False, default="[]")
    marcha_totals = db.Column(db.Text, nullable=False, default="{}")
    km_totals = db.Column(db.Text, nullable=False, default="{}")
    ralenti_totals = db.Column(db.Text, nullable=False, default="{}")

    events = db.relationship(
        "RalentiEvent",
        backref="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RalentiEvent(db.Model):
    __tablename__ = "ralenti_events"

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(
        db.String(512),
        db.ForeignKey("ralenti_files.name", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    persona = db.Column(db.String(255), nullable=False, index=True)
    vehiculo = db.Column(db.String(255), nullable=False, default="")
    referencia = db.Column(db.String(512), nullable=False, default="Sin referencia")
    fecha = db.Column(db.String(64), nullable=False, default="")
    mes = db.Column(db.String(32), nullable=False, default="", index=True)
    hora = db.Column(db.Integer, nullable=False, default=0)
    dur_min = db.Column(db.Float, nullable=False, default=0)
    marcha_min = db.Column(db.Float, nullable=False, default=0)
    litros = db.Column(db.Float, nullable=False, default=0)


class RalentiConfig(db.Model):
    __tablename__ = "ralenti_config"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
