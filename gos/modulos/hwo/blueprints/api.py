from flask import Blueprint, jsonify, request
from flask_login import login_required

from gos.modulos.hwo import storage

bp = Blueprint("hwo_api", __name__)


@bp.route("/health")
@login_required
def health():
    return jsonify({"ok": True, "ts": int(__import__("time").time() * 1000)})


@bp.route("/datasets", methods=["GET"])
@login_required
def list_datasets():
    try:
        return jsonify(storage.get_all_datasets())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/datasets/by-name", methods=["GET"])
@login_required
def get_dataset_by_name():
    name = (request.args.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Falta el parámetro name"}), 400
    try:
        row = storage.get_dataset(name)
        if not row:
            return jsonify({"error": "No encontrado"}), 404
        return jsonify(
            {
                "name": row["name"],
                "savedAt": row.get("savedAt"),
                "configRaw": row.get("configRaw"),
                "rowsRaw": row.get("rowsRaw"),
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/datasets/by-name", methods=["DELETE"])
@login_required
def delete_dataset_by_name():
    name = (request.args.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Falta el parámetro name"}), 400
    try:
        storage.delete_dataset(name)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/datasets/<path:name>", methods=["GET"])
@login_required
def get_dataset(name: str):
    try:
        row = storage.get_dataset(name)
        if not row:
            return jsonify({"error": "No encontrado"}), 404
        return jsonify(
            {
                "name": row["name"],
                "savedAt": row.get("savedAt"),
                "configRaw": row.get("configRaw"),
                "rowsRaw": row.get("rowsRaw"),
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/datasets/rename", methods=["PUT"])
@login_required
def rename_dataset():
    try:
        payload = request.get_json(silent=True) or {}
        old_name = (payload.get("oldName") or "").strip()
        new_name = (payload.get("newName") or "").strip()
        if not old_name or not new_name:
            return jsonify({"error": "Faltan campos: oldName, newName"}), 400
        storage.rename_dataset(old_name, new_name)
        return jsonify({"ok": True, "name": new_name})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/datasets", methods=["POST"])
@login_required
def save_dataset():
    try:
        payload = request.get_json(silent=True) or {}
        name = payload.get("name")
        config_raw = payload.get("configRaw")
        rows_raw = payload.get("rowsRaw")
        if not name or config_raw is None or rows_raw is None:
            return jsonify({"error": "Faltan campos: name, configRaw, rowsRaw"}), 400
        storage.save_dataset(name, config_raw, rows_raw)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/datasets/<path:name>", methods=["DELETE"])
@login_required
def delete_dataset(name: str):
    try:
        storage.delete_dataset(name)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/datasets", methods=["DELETE"])
@login_required
def clear_datasets():
    try:
        storage.clear_datasets()
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/modalidad", methods=["GET"])
@login_required
def get_modalidad():
    try:
        return jsonify(storage.get_all_modalidad())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/modalidad", methods=["PUT"])
@login_required
def put_modalidad():
    try:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Body inválido"}), 400
        storage.save_modalidad(payload)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
