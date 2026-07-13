from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("ralenti_main", __name__)


@bp.route("/")
@login_required
def index():
    return render_template("ralenti/shell.html")


@bp.route("/app/")
@login_required
def app():
    return render_template("ralenti/app.html")
