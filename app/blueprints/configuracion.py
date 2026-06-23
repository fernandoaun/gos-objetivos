from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Area, PlaneamientoConfig, Responsable, Sector
from app.utils.auth_decorators import requiere_rol

bp = Blueprint("configuracion", __name__)


def _empresa_id():
    return current_user.empresa_id


@bp.route("/")
@login_required
def index():
    tab = request.args.get("tab", "sectores")
    eid = _empresa_id()
    sectores = Sector.query.filter_by(empresa_id=eid).order_by(Sector.codigo).all()
    areas = Area.query.filter_by(empresa_id=eid).order_by(Area.codigo).all()
    responsables = (
        Responsable.query.filter_by(empresa_id=eid).order_by(Responsable.codigo).all()
    )
    config = PlaneamientoConfig.query.filter_by(empresa_id=eid).first()
    return render_template(
        "configuracion/index.html",
        tab=tab,
        sectores=sectores,
        areas=areas,
        responsables=responsables,
        config=config,
        sectores_select=sectores,
    )


@bp.route("/sectores", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente")
def crear_sector():
    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    if not codigo or not nombre:
        flash("Código y nombre son obligatorios.", "warning")
        return redirect(url_for("configuracion.index", tab="sectores"))
    if Sector.query.filter_by(empresa_id=_empresa_id(), codigo=codigo).first():
        flash(f"Ya existe el sector {codigo}.", "danger")
        return redirect(url_for("configuracion.index", tab="sectores"))
    db.session.add(Sector(empresa_id=_empresa_id(), codigo=codigo, nombre=nombre))
    db.session.commit()
    flash("Sector creado.", "success")
    return redirect(url_for("configuracion.index", tab="sectores"))


@bp.route("/sectores/<int:id>/eliminar", methods=["POST"])
@login_required
@requiere_rol("admin")
def eliminar_sector(id):
    sector = Sector.query.filter_by(id=id, empresa_id=_empresa_id()).first_or_404()
    sector.activo = False
    db.session.commit()
    flash("Sector desactivado.", "info")
    return redirect(url_for("configuracion.index", tab="sectores"))


@bp.route("/areas", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente")
def crear_area():
    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    sector_id = request.form.get("sector_id") or None
    if sector_id:
        sector_id = int(sector_id)
    if not codigo or not nombre:
        flash("Código y nombre son obligatorios.", "warning")
        return redirect(url_for("configuracion.index", tab="areas"))
    db.session.add(
        Area(
            empresa_id=_empresa_id(),
            codigo=codigo,
            nombre=nombre,
            sector_id=sector_id,
        )
    )
    db.session.commit()
    flash("Área creada.", "success")
    return redirect(url_for("configuracion.index", tab="areas"))


@bp.route("/responsables", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente")
def crear_responsable():
    codigo = request.form.get("codigo", "").strip()
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip() or None
    area_id = request.form.get("area_id") or None
    if area_id:
        area_id = int(area_id)
    if not codigo or not nombre:
        flash("Código y nombre son obligatorios.", "warning")
        return redirect(url_for("configuracion.index", tab="responsables"))
    db.session.add(
        Responsable(
            empresa_id=_empresa_id(),
            codigo=codigo,
            nombre=nombre,
            email=email,
            area_id=area_id,
        )
    )
    db.session.commit()
    flash("Responsable creado.", "success")
    return redirect(url_for("configuracion.index", tab="responsables"))


@bp.route("/umbrales", methods=["POST"])
@login_required
@requiere_rol("admin")
def guardar_umbrales():
    config = PlaneamientoConfig.query.filter_by(empresa_id=_empresa_id()).first()
    if not config:
        config = PlaneamientoConfig(empresa_id=_empresa_id())
        db.session.add(config)
    config.umbral_verde = request.form.get("umbral_verde", 90)
    config.umbral_amarillo = request.form.get("umbral_amarillo", 70)
    config.auto_plan_accion = bool(request.form.get("auto_plan_accion"))
    db.session.commit()
    flash("Configuración guardada.", "success")
    return redirect(url_for("configuracion.index", tab="umbrales"))
