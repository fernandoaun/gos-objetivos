from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from gos.models import Usuario

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = Usuario.query.filter_by(email=email, activo=True).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("main.index"))

        flash("Email o contraseña incorrectos.", "danger")

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
