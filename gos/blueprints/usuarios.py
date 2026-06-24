from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from gos.models import Usuario
from gos.models.usuario import ROL_LABELS, ROLES
from gos.services import usuario_service
from gos.utils.auth_decorators import requiere_admin

bp = Blueprint("usuarios", __name__)


@bp.route("/")
@requiere_admin
def index():
    usuarios = usuario_service.listar_usuarios_empresa(current_user.empresa_id)
    return render_template(
        "usuarios/index.html",
        usuarios=usuarios,
        roles=ROLES,
        rol_labels=ROL_LABELS,
    )


@bp.route("/", methods=["POST"])
@requiere_admin
def crear():
    user, error = usuario_service.crear_usuario(
        empresa_id=current_user.empresa_id,
        email=request.form.get("email", ""),
        nombre=request.form.get("nombre", ""),
        password=request.form.get("password", ""),
        rol=request.form.get("rol", "usuario"),
    )
    if error:
        flash(error, "danger")
    else:
        flash(f"Usuario {user.email} creado correctamente.", "success")
    return redirect(url_for("usuarios.index"))


@bp.route("/<int:user_id>/editar", methods=["POST"])
@requiere_admin
def editar(user_id: int):
    user = Usuario.query.filter_by(id=user_id, empresa_id=current_user.empresa_id).first_or_404()

    activo = request.form.get("activo") == "on"
    if user.id == current_user.id and not activo:
        flash("No podés desactivar tu propio usuario.", "warning")
        return redirect(url_for("usuarios.index"))

    error = usuario_service.actualizar_usuario(
        user,
        nombre=request.form.get("nombre", ""),
        rol=request.form.get("rol", user.rol),
        activo=activo,
        password=request.form.get("password") or None,
    )
    if error:
        flash(error, "danger")
    else:
        flash(f"Usuario {user.email} actualizado.", "success")
    return redirect(url_for("usuarios.index"))
