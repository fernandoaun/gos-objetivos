from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from gos.models import Usuario
from gos.services import auth_service

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        try:
            user = Usuario.query.filter_by(email=email, activo=True).first()
        except Exception:
            from gos.extensions import db

            db.session.rollback()
            flash(
                "Error de base de datos al iniciar sesión. Revisá los logs de Render o /gos/objetivos/api/v1/health?db=1.",
                "danger",
            )
            return render_template("auth/login.html")

        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("main.index"))

        flash("Email o contraseña incorrectos.", "danger")

    return render_template("auth/login.html")


@bp.route("/cambiar-contrasena", methods=["GET", "POST"])
@login_required
def cambiar_contrasena():
    if request.method == "POST":
        error = auth_service.cambiar_contraseña(
            current_user,
            actual=request.form.get("actual", ""),
            nueva=request.form.get("nueva", ""),
            confirmacion=request.form.get("confirmacion", ""),
        )
        if error:
            flash(error, "danger")
        else:
            flash("Contraseña actualizada correctamente.", "success")
            return redirect(url_for("main.index"))

    return render_template("auth/cambiar_contrasena.html")


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
