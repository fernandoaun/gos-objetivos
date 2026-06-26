from sqlalchemy import Column, Integer, String, Text, UniqueConstraint

from gos.modulos.hwo.database import Base


class HwoDataset(Base):
    __tablename__ = "hwo_datasets"
    __table_args__ = (UniqueConstraint("name", name="uq_hwo_dataset_name"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    saved_at = Column(Integer, nullable=False)
    config_raw = Column(Text, nullable=False)
    rows_raw = Column(Text, nullable=False)


class HwoModalidad(Base):
    __tablename__ = "hwo_modalidad"

    equipo = Column(String, primary_key=True)
    schedule = Column(String, nullable=False)
