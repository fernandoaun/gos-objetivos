from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint

from gos.modulos.vacaciones.database import Base


class Registro(Base):
    __tablename__ = "registros"
    __table_args__ = (UniqueConstraint("fecha", "empleado", name="uq_fecha_empleado"),)

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    empleado = Column(String, nullable=False)
    sector = Column(String)
    servicio = Column(String)
    centro = Column(String)
    situacion = Column(String)
    total_horas = Column(Float, default=0)
    hs_viaje = Column(Float, default=0)
    hs50 = Column(Float, default=0)
    hs_noc = Column(Float, default=0)
    hs_noc50 = Column(Float, default=0)
    hs100 = Column(Float, default=0)
    viandas = Column(Integer, default=0)
    v_desayuno = Column(Integer, default=0)
    d_normales = Column(Integer, default=0)
    ausente = Column(Integer, default=0)
    fr_trabajados = Column(Integer, default=0)
    feriados = Column(Integer, default=0)
    enfermedad = Column(Integer, default=0)
    traslado = Column(Integer, default=0)
    vacaciones = Column(Integer, default=0)
    licencia = Column(Integer, default=0)
    suspension = Column(Integer, default=0)
    accidente = Column(Integer, default=0)
    francos_comp = Column(Integer, default=0)


class Vacacion(Base):
    __tablename__ = "vacaciones"
    __table_args__ = (UniqueConstraint("legajo", "anio", name="uq_legajo_anio"),)

    id = Column(Integer, primary_key=True, index=True)
    legajo = Column(Integer)
    empleado = Column(String, nullable=False)
    fecha_ingreso = Column(Date)
    sector = Column(String)
    anio = Column(Integer, nullable=False)
    dias_disponibles = Column(Integer, default=0)
    dias_tomados = Column(Integer, default=0)
    dias_pendientes = Column(Integer, default=0)
