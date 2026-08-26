from flask import Blueprint, current_app, redirect, render_template, url_for
from flask_login import login_required

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def index():
    if current_app.config.get("GOS_APP_MODE") == "capacitacion":
        return redirect(url_for("capacitacion_main.index"))
    return render_template("home.html")
