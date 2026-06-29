from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from gos.models import Perfil
from gos.services import perfil_service
from gos.services.modulo_service import MODULO_CODES, MODULO_LABELS
from gos.utils.auth_decorators import requiere_admin

bp = Blueprint("perfiles", __name__)


@bp.route("/")
@requiere_admin
def index():
    perfiles = perfil_service.listar_perfiles_empresa(current_user.empresa_id)
    return render_template(
        "perfiles/index.html",
        perfiles=perfiles,
        modulo_codes=MODULO_CODES,
        modulo_labels=MODULO_LABELS,
    )


@bp.route("/", methods=["POST"])
@requiere_admin
def crear():
    perfil, error = perfil_service.crear_perfil(
        empresa_id=current_user.empresa_id,
        nombre=request.form.get("nombre", ""),
        modulos=request.form.getlist("modulos"),
    )
    if error:
        flash(error, "danger")
    else:
        flash(f"Perfil «{perfil.nombre}» creado correctamente.", "success")
    return redirect(url_for("perfiles.index"))


@bp.route("/<int:perfil_id>/editar", methods=["POST"])
@requiere_admin
def editar(perfil_id: int):
    perfil = Perfil.query.filter_by(
        id=perfil_id, empresa_id=current_user.empresa_id
    ).first_or_404()

    error = perfil_service.actualizar_perfil(
        perfil,
        nombre=request.form.get("nombre", ""),
        modulos=request.form.getlist("modulos"),
    )
    if error:
        flash(error, "danger")
    else:
        flash(f"Perfil «{perfil.nombre}» actualizado.", "success")
    return redirect(url_for("perfiles.index"))


@bp.route("/<int:perfil_id>/eliminar", methods=["POST"])
@requiere_admin
def eliminar(perfil_id: int):
    perfil = Perfil.query.filter_by(
        id=perfil_id, empresa_id=current_user.empresa_id
    ).first_or_404()

    error = perfil_service.eliminar_perfil(perfil)
    if error:
        flash(error, "danger")
    else:
        flash("Perfil eliminado.", "success")
    return redirect(url_for("perfiles.index"))
