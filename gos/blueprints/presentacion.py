"""API y descarga de presentaciones PPTX por módulo."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required

from gos.services import presentacion_service

bp = Blueprint("presentacion", __name__)


@bp.get("/api/presentacion/catalogo")
@login_required
def catalogo():
    return jsonify({"ok": True, "modulos": presentacion_service.catalogo_presentaciones()})


@bp.post("/api/presentacion/generar")
@login_required
def generar():
    data = request.get_json(silent=True) or {}
    module_code = (data.get("module") or data.get("modulo") or "").strip()
    submodulos = data.get("submodulos") or data.get("submodules") or []
    if isinstance(submodulos, str):
        submodulos = [s.strip() for s in submodulos.split(",") if s.strip()]
    if not module_code:
        return jsonify({"ok": False, "error": "Indicá el módulo."}), 400
    try:
        payload, filename = presentacion_service.generar_pptx(module_code, submodulos or None)
    except PermissionError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "No se pudo generar la presentación."}), 500

    from io import BytesIO

    return send_file(
        BytesIO(payload),
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name=filename,
    )
