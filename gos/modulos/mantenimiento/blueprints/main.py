from flask import Blueprint, render_template, request
from flask_login import login_required

bp = Blueprint("mantenimiento_main", __name__)


@bp.route("/")
@login_required
def index():
    return render_template("mantenimiento/shell.html", view="plan")


@bp.route("/vtv")
@login_required
def vtv():
    return render_template("mantenimiento/shell.html", view="vtv")


@bp.route("/importar")
@login_required
def importar():
    return render_template("mantenimiento/shell.html", view="importar")


@bp.route("/app/")
@login_required
def app():
    view = request.args.get("view", "plan")
    return render_template("mantenimiento/app.html", initial_view=view)
