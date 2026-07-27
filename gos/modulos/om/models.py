from datetime import datetime

from gos.extensions import db


class OmModule(db.Model):
    __tablename__ = "om_modules"
    __table_args__ = (db.UniqueConstraint("code", name="uq_om_modules_code"),)

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="active")
    schedule = db.Column(db.String(128))
    guard = db.Column(db.String(128))
    location = db.Column(db.String(128))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    deleted_at = db.Column(db.DateTime)

    personnel = db.relationship(
        "OmPersonnel",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="OmPersonnel.sort_order, OmPersonnel.id",
    )
    items = db.relationship(
        "OmItem",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="OmItem.sort_order, OmItem.id",
    )


class OmPersonnel(db.Model):
    __tablename__ = "om_module_personnel"

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(
        db.Integer, db.ForeignKey("om_modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(128))
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    module = db.relationship("OmModule", back_populates="personnel")
    phones = db.relationship(
        "OmPhone",
        back_populates="personnel",
        cascade="all, delete-orphan",
    )


class OmPhone(db.Model):
    __tablename__ = "om_personnel_phones"

    id = db.Column(db.Integer, primary_key=True)
    personnel_id = db.Column(
        db.Integer,
        db.ForeignKey("om_module_personnel.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = db.Column(db.String(64), nullable=False)
    number = db.Column(db.String(64), nullable=False)

    personnel = db.relationship("OmPersonnel", back_populates="phones")


class OmItem(db.Model):
    __tablename__ = "om_module_items"

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(
        db.Integer, db.ForeignKey("om_modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind = db.Column(db.String(16), nullable=False)  # unit | tool | supply
    value = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    module = db.relationship("OmModule", back_populates="items")


class OmAuditLog(db.Model):
    __tablename__ = "om_audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True, index=True)
    action = db.Column(db.String(32), nullable=False)
    entity = db.Column(db.String(32), nullable=False)
    entity_id = db.Column(db.String(64))
    before = db.Column(db.JSON)
    after = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
