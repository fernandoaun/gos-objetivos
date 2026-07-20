from flask import Blueprint, jsonify
from flask_login import login_required

bp = Blueprint("mantenimiento_api", __name__)


@bp.route("/health")
@login_required
def health():
    return jsonify({"ok": True, "ts": int(__import__("time").time() * 1000)})
