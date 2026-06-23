from flask import Blueprint, render_template
from flask_login import login_required

def placeholder_blueprint(name: str, url_prefix: str, title: str, message: str):
    bp = Blueprint(name, __name__, url_prefix=url_prefix)

    @bp.route("/")
    @login_required
    def index():
        return render_template(
            "components/placeholder.html",
            title=title,
            message=message,
        )

    return bp
