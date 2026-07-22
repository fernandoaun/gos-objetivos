from flask import Blueprint, render_template, request
from flask_login import login_required

bp = Blueprint("vacaciones_main", __name__)


@bp.route("/")
@login_required
def index():
    return render_template("vacaciones/shell.html", view="vacaciones")


@bp.route("/tot-hs")
@login_required
def tot_hs():
    return render_template("vacaciones/shell.html", view="tot_hs")


@bp.route("/importar")
@login_required
def importar():
    return render_template("vacaciones/shell.html", view="importar")


@bp.route("/app/")
@login_required
def app():
    view = request.args.get("view", "vacaciones")
    return render_template("vacaciones/app.html", initial_view=view)
