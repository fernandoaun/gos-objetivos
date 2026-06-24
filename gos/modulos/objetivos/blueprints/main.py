from flask import Blueprint, redirect, url_for

bp = Blueprint("objetivos_main", __name__)


@bp.route("/")
def index():
    return redirect(url_for("objetivos_dashboard.index"))
