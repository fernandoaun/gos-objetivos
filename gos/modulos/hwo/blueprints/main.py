from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("hwo_main", __name__)


@bp.route("/")
@login_required
def index():
    return render_template("hwo/shell.html")


@bp.route("/app/")
@login_required
def app():
    return render_template("hwo/app.html")
