import os
import tempfile
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from app.version import APP_VERSION

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.route("/health")
def health():
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


@bp.route("/admin/import-db", methods=["POST"])
def import_db():
    """Restaura backup SQLite en la base PostgreSQL del servicio (misma que usa la web)."""
    expected = os.environ.get("GOS_IMPORT_SECRET", "")
    if not expected or request.headers.get("X-Import-Secret") != expected:
        return jsonify({"ok": False, "error": "No autorizado"}), 403

    upload = request.files.get("database")
    if not upload or not upload.filename:
        return jsonify({"ok": False, "error": "Falta archivo database"}), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            upload.save(tmp.name)
            tmp_path = Path(tmp.name)

        from app.services.import_service import importar_sqlite

        target_url = current_app.config["SQLALCHEMY_DATABASE_URI"]
        counts = importar_sqlite(tmp_path, target_url)
        return jsonify({
            "ok": True,
            "imported": {k: v for k, v in counts.items() if v},
        })
    except Exception as exc:
        current_app.logger.exception("import-db failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
