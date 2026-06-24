from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("capacitacion_main", __name__)


@bp.route("/")
@login_required
def index():
    return render_template("capacitacion/shell.html", view="panel")


@bp.route("/programas")
@login_required
def programas():
    return render_template("capacitacion/shell.html", view="programas")


@bp.route("/personas")
@login_required
def personas():
    return render_template("capacitacion/shell.html", view="personas")


@bp.route("/catalogos")
@login_required
def catalogos():
    return render_template("capacitacion/shell.html", view="catalogos")


@bp.route("/app/")
@login_required
def app():
    from flask import request

    view = request.args.get("view", "panel")
    return render_template(
        "capacitacion/app.html",
        initial_view=view,
        api_base="/gos/capacitacion/api",
    )
