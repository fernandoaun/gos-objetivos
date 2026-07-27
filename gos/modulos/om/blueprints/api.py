from flask import Blueprint, jsonify, request, Response
from flask_login import current_user, login_required

from gos import env
from gos.modulos.om import services
from gos.modulos.om.services import (
    OmConflictError,
    OmNotFoundError,
    OmValidationError,
)

bp = Blueprint("om_api", __name__)


def _import_auth_ok() -> bool:
    provided = (request.headers.get("X-Import-Secret") or request.args.get("secret") or "").strip()
    return env.import_auth_ok(provided)


def _ok(data=None, message: str = "", status: int = 200):
    return jsonify(
        {
            "success": True,
            "data": data,
            "message": message,
            "errors": [],
            "request_id": request.headers.get("X-Request-Id") or "",
        }
    ), status


def _err(message: str, status: int = 400, errors=None):
    return jsonify(
        {
            "success": False,
            "data": None,
            "message": message,
            "errors": errors or [],
            "request_id": request.headers.get("X-Request-Id") or "",
        }
    ), status


def _is_admin() -> bool:
    return bool(
        current_user.is_authenticated
        and (current_user.es_administrador() or current_user.es_angel())
    )


@bp.route("/me")
@login_required
def me():
    role = "admin" if _is_admin() else "editor"
    return _ok(
        {
            "id": current_user.id,
            "username": current_user.email or current_user.nombre,
            "nombre": current_user.nombre,
            "role": role,
        }
    )


@bp.route("/catalog/personal")
@login_required
def catalog_personal():
    try:
        items = services.catalog_personal(
            current_user.empresa_id, q=request.args.get("q")
        )
        return _ok(items)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@bp.route("/catalog/unidades")
@login_required
def catalog_unidades():
    try:
        return _ok(services.catalog_unidades())
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@bp.route("/modules", methods=["GET"])
@login_required
def list_modules():
    try:
        return _ok(services.list_modules())
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@bp.route("/modules/export", methods=["GET"])
@login_required
def export_modules():
    if not _is_admin():
        return _err("Solo administradores pueden exportar el respaldo", 403)
    modules = services.list_modules()
    from datetime import date
    import json

    payload = json.dumps(modules, ensure_ascii=False, indent=2)
    filename = f"modulos_backup_{date.today().isoformat()}.json"
    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@bp.route("/modules", methods=["POST"])
@login_required
def create_module():
    try:
        created = services.create_module(request.get_json(silent=True) or {}, current_user.id)
        return _ok(created, "Modulo creado", 201)
    except OmValidationError as exc:
        return _err(exc.message, 400, exc.field_errors)
    except OmConflictError as exc:
        return _err(exc.message, 409)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@bp.route("/modules/<int:module_id>", methods=["PUT"])
@login_required
def update_module(module_id: int):
    try:
        updated = services.update_module(
            module_id, request.get_json(silent=True) or {}, current_user.id
        )
        return _ok(updated, "Modulo actualizado")
    except OmValidationError as exc:
        return _err(exc.message, 400, exc.field_errors)
    except OmConflictError as exc:
        return _err(exc.message, 409)
    except OmNotFoundError as exc:
        return _err(exc.message, 404)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@bp.route("/modules/<int:module_id>", methods=["DELETE"])
@login_required
def delete_module(module_id: int):
    try:
        services.soft_delete_module(module_id, current_user.id)
        return _ok(None, "Modulo eliminado")
    except OmNotFoundError as exc:
        return _err(exc.message, 404)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@bp.route("/audit", methods=["GET"])
@login_required
def audit():
    if not _is_admin():
        return _err("Solo administradores pueden ver la actividad", 403)
    try:
        limit = int(request.args.get("limit") or 50)
    except ValueError:
        limit = 50
    try:
        offset = int(request.args.get("offset") or 0)
    except ValueError:
        offset = 0
    try:
        return _ok(services.list_audit(limit=limit, offset=offset))
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), 500)


@bp.route("/admin/import-legacy", methods=["POST"])
def import_legacy():
    """Importa módulos O&M desde JSON (idempotente por code). Usa X-Import-Secret."""
    if not _import_auth_ok():
        return jsonify({
            "ok": False,
            "error": "No autorizado. Configurá GOS_IMPORT_SECRET y enviá X-Import-Secret.",
        }), 403

    payload = request.get_json(silent=True)
    if payload is None and request.files.get("file"):
        import json

        raw = request.files["file"].read().decode("utf-8")
        payload = json.loads(raw)

    if isinstance(payload, dict) and "modules" in payload:
        modules = payload["modules"]
    else:
        modules = payload

    if not isinstance(modules, list):
        return jsonify({"ok": False, "error": "Se espera un array JSON de módulos"}), 400

    result = services.import_modules_payload(modules, user_id=None)
    return jsonify({"ok": True, **result})
