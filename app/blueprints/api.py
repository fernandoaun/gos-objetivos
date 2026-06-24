from flask import Blueprint, jsonify

from app.version import APP_VERSION

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.route("/health")
def health():
    from flask import request

    payload = {
        "ok": True,
        "service": "gos-objetivos",
        "version": APP_VERSION,
        "features": ["foda-word", "foda-crud", "foda-pdf"],
    }
    if request.args.get("db") == "1":
        from app.models import FodaItem, KpiIndicador, Objetivo

        payload["db"] = {
            "foda_items": FodaItem.query.count(),
            "objetivos": Objetivo.query.count(),
            "kpi_indicadores": KpiIndicador.query.count(),
        }
    return jsonify(payload)
