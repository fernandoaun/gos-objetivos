from flask import Blueprint, jsonify, request
from flask_login import login_required

from gos.modulos.ralenti import storage

bp = Blueprint("ralenti_api", __name__)


@bp.route("/health")
@login_required
def health():
    return jsonify({"ok": True, "ts": int(__import__("time").time() * 1000)})


@bp.route("/events", methods=["GET"])
@login_required
def get_events():
    try:
        return jsonify(
            storage.list_events(
                vehiculo=request.args.get("vehiculo") or None,
                persona=request.args.get("persona") or None,
                mes=request.args.get("mes") or None,
                referencia=request.args.get("referencia") or None,
            )
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/events/filters", methods=["GET"])
@login_required
def get_filters():
    try:
        return jsonify(storage.event_filters())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/files", methods=["GET"])
@login_required
def list_files():
    try:
        return jsonify(storage.list_files())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/files/import", methods=["POST"])
@login_required
def import_file():
    try:
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        events = payload.get("events")
        if not name or not isinstance(events, list):
            return jsonify({"error": "Faltan campos: name, events"}), 400
        result = storage.import_file(
            name=name,
            events=events,
            persons=payload.get("persons") or [],
            marcha_totals=payload.get("marcha_totals") or {},
            km_totals=payload.get("km_totals") or {},
            ralenti_totals=payload.get("ralenti_totals") or {},
        )
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/files/<path:filename>", methods=["DELETE"])
@login_required
def delete_file(filename: str):
    try:
        storage.delete_file(filename)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/config", methods=["GET"])
@login_required
def get_config():
    try:
        return jsonify(storage.get_config())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/config", methods=["PUT"])
@login_required
def put_config():
    try:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Body inválido"}), 400
        storage.update_config(payload)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
