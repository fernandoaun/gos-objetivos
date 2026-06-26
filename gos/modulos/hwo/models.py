from gos.extensions import db


class HwoDataset(db.Model):
    __tablename__ = "hwo_datasets"
    __table_args__ = (db.UniqueConstraint("name", name="uq_hwo_dataset_name"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(512), nullable=False, index=True)
    saved_at = db.Column(db.BigInteger, nullable=False)
    config_raw = db.Column(db.Text, nullable=False)
    rows_raw = db.Column(db.Text, nullable=False)


class HwoModalidad(db.Model):
    __tablename__ = "hwo_modalidad"

    equipo = db.Column(db.String(255), primary_key=True)
    schedule = db.Column(db.String(32), nullable=False)
