from flask import Blueprint, render_template
from flask_login import current_user, login_required

bp = Blueprint("om_main", __name__)


@bp.route("/")
@login_required
def index():
    return render_template("om/shell.html")


@bp.route("/app/")
@login_required
def app():
    is_admin = current_user.es_administrador() or current_user.es_angel()
    return render_template(
        "om/app.html",
        om_user={
            "username": current_user.email or current_user.nombre,
            "nombre": current_user.nombre,
            "role": "admin" if is_admin else "editor",
        },
        api_base="/gos/om/api",
        logout_url="/auth/logout",
        home_url="/",
    )
