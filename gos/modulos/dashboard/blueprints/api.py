import time

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from gos.modulos.dashboard import services

bp = Blueprint("dashboard_api", __name__)


@bp.route("/health")
@login_required
def health():
    return jsonify({"ok": True, "ts": int(time.time() * 1000)})


@bp.route("/summary")
@login_required
def summary():
    try:
        data = services.build_summary(current_user.empresa_id)
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
