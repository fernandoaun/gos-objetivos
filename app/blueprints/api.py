from flask import Blueprint, jsonify

from app.version import APP_VERSION

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.route("/health")
def health():
    return jsonify({
        "ok": True,
        "service": "gos-objetivos",
        "version": APP_VERSION,
        "features": ["foda-word", "foda-crud", "foda-pdf"],
    })
