from gos.extensions import db


class Registro(db.Model):
    __tablename__ = "registros"
    __table_args__ = (db.UniqueConstraint("fecha", "empleado", name="uq_fecha_empleado"),)

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    empleado = db.Column(db.String, nullable=False)
    sector = db.Column(db.String)
    servicio = db.Column(db.String)
    centro = db.Column(db.String)
    situacion = db.Column(db.String)
    total_horas = db.Column(db.Float, default=0)
    hs_viaje = db.Column(db.Float, default=0)
    hs50 = db.Column(db.Float, default=0)
    hs_noc = db.Column(db.Float, default=0)
    hs_noc50 = db.Column(db.Float, default=0)
    hs100 = db.Column(db.Float, default=0)
    viandas = db.Column(db.Integer, default=0)
    v_desayuno = db.Column(db.Integer, default=0)
    d_normales = db.Column(db.Integer, default=0)
    ausente = db.Column(db.Integer, default=0)
    fr_trabajados = db.Column(db.Integer, default=0)
    feriados = db.Column(db.Integer, default=0)
    enfermedad = db.Column(db.Integer, default=0)
    traslado = db.Column(db.Integer, default=0)
    vacaciones = db.Column(db.Integer, default=0)
    licencia = db.Column(db.Integer, default=0)
    suspension = db.Column(db.Integer, default=0)
    accidente = db.Column(db.Integer, default=0)
    francos_comp = db.Column(db.Integer, default=0)


class Vacacion(db.Model):
    __tablename__ = "vacaciones"
    __table_args__ = (db.UniqueConstraint("legajo", "anio", name="uq_legajo_anio"),)

    id = db.Column(db.Integer, primary_key=True)
    legajo = db.Column(db.Integer)
    empleado = db.Column(db.String, nullable=False)
    fecha_ingreso = db.Column(db.Date)
    sector = db.Column(db.String)
    anio = db.Column(db.Integer, nullable=False)
    dias_disponibles = db.Column(db.Integer, default=0)
    dias_tomados = db.Column(db.Integer, default=0)
    dias_pendientes = db.Column(db.Integer, default=0)
