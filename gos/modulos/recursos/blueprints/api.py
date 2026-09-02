import os
import tempfile

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from gos.extensions import db
from gos.modulos.recursos import services
from gos.modulos.recursos.importer import import_planilla
from gos.modulos.recursos.services import RecNotFoundError, RecValidationError

bp = Blueprint("recursos_api", __name__)


@bp.route("/resumen")
@login_required
def resumen():
    return jsonify(services.resumen())


@bp.route("/destinos")
@login_required
def destinos():
    return jsonify(services.destinos_payload())


@bp.route("/destinos", methods=["POST"])
@login_required
def crear_destino():
    payload = request.get_json(silent=True) or {}
    try:
        data = services.crear_servicio(
            nombre=payload.get("nombre") or "",
            equipo=payload.get("equipo") or payload.get("centro"),
            cupos=payload.get("cupos"),
            user_id=current_user.id,
        )
        return jsonify({"ok": True, "destino": data})
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/destinos/<int:destino_id>", methods=["POST", "PATCH"])
@login_required
def actualizar_destino(destino_id: int):
    payload = request.get_json(silent=True) or {}
    equipo_kw = None
    tocar_equipo = "equipo" in payload or "centro" in payload
    if tocar_equipo:
        equipo_kw = payload.get("equipo")
        if equipo_kw is None:
            equipo_kw = payload.get("centro")
    try:
        data = services.actualizar_servicio(
            destino_id,
            nombre=payload.get("nombre"),
            equipo=equipo_kw if tocar_equipo else None,
            cupos=payload.get("cupos"),
            user_id=current_user.id,
        )
        return jsonify({"ok": True, "destino": data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/destinos/<int:destino_id>/baja", methods=["POST"])
@login_required
def dar_de_baja_destino(destino_id: int):
    try:
        data = services.dar_de_baja_servicio(destino_id, user_id=current_user.id)
        return jsonify({"ok": True, "destino": data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/destinos/<int:destino_id>/equipo", methods=["POST", "PATCH"])
@login_required
def mover_equipo(destino_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        data = services.mover_equipo(
            payload.get("equipo") or "",
            destino_id,
            desde_id=payload.get("desde_id"),
            user_id=current_user.id,
        )
        return jsonify({"ok": True, **data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/centros")
@login_required
def centros():
    bajas = request.args.get("bajas") == "1"
    return jsonify(services.centros_payload(activos=None if bajas else True))


@bp.route("/centros", methods=["POST"])
@login_required
def crear_centro():
    payload = request.get_json(silent=True) or {}
    try:
        data = services.crear_centro(
            codigo=payload.get("codigo") or "",
            nombre=payload.get("nombre"),
            destino_id=payload.get("destino_id"),
            user_id=current_user.id,
        )
        return jsonify({"ok": True, "centro": data})
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/centros/mover", methods=["POST"])
@login_required
def mover_centro():
    payload = request.get_json(silent=True) or {}
    try:
        data = services.mover_equipo(
            payload.get("equipo") or payload.get("codigo") or "",
            payload.get("destino_id"),
            desde_id=payload.get("desde_id"),
            user_id=current_user.id,
        )
        return jsonify({"ok": True, **data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/centros/<int:centro_id>", methods=["POST", "PATCH"])
@login_required
def actualizar_centro(centro_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        data = services.actualizar_centro(
            centro_id,
            codigo=payload.get("codigo"),
            nombre=payload.get("nombre"),
            destino_id=payload.get("destino_id"),
            tocar_destino="destino_id" in payload,
            user_id=current_user.id,
        )
        return jsonify({"ok": True, "centro": data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/centros/<int:centro_id>/baja", methods=["POST"])
@login_required
def dar_de_baja_centro(centro_id: int):
    try:
        data = services.dar_de_baja_centro(centro_id, user_id=current_user.id)
        return jsonify({"ok": True, "centro": data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404


@bp.route("/centros/<int:centro_id>/reactivar", methods=["POST"])
@login_required
def reactivar_centro(centro_id: int):
    try:
        data = services.reactivar_centro(centro_id, user_id=current_user.id)
        return jsonify({"ok": True, "centro": data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404


@bp.route("/unidades/<int:unidad_id>/destino", methods=["POST", "PATCH"])
@login_required
def cambiar_destino(unidad_id: int):
    payload = request.get_json(silent=True) or {}
    destino_id = payload.get("destino_id")
    try:
        data = services.asignar_destino(unidad_id, destino_id, user_id=current_user.id)
        return jsonify({"ok": True, "unidad": data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/unidades", methods=["POST"])
@login_required
def crear_unidad():
    payload = request.get_json(silent=True) or {}
    try:
        data = services.crear_unidad(
            interno=payload.get("interno") or "",
            dominio=payload.get("dominio"),
            tipo=payload.get("tipo"),
            contratista=payload.get("contratista"),
            es_centro=bool(payload.get("es_centro")),
            destino_id=payload.get("destino_id"),
            user_id=current_user.id,
        )
        return jsonify({"ok": True, "unidad": data})
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/unidades/<int:unidad_id>/baja", methods=["POST"])
@login_required
def dar_de_baja(unidad_id: int):
    try:
        data = services.dar_de_baja(unidad_id, user_id=current_user.id)
        return jsonify({"ok": True, "unidad": data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404


@bp.route("/unidades/<int:unidad_id>/reactivar", methods=["POST"])
@login_required
def reactivar_unidad(unidad_id: int):
    try:
        data = services.reactivar_unidad(unidad_id, user_id=current_user.id)
        return jsonify({"ok": True, "unidad": data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404


@bp.route("/unidades/<int:unidad_id>/centro", methods=["POST", "PATCH"])
@login_required
def marcar_centro(unidad_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        data = services.marcar_centro(unidad_id, bool(payload.get("es_centro")), user_id=current_user.id)
        return jsonify({"ok": True, "unidad": data})
    except RecNotFoundError as exc:
        return jsonify({"ok": False, "error": exc.message}), 404
    except RecValidationError as exc:
        return jsonify({"ok": False, "error": exc.message}), 400


@bp.route("/importar", methods=["POST"])
@login_required
def importar():
    upload = request.files.get("file") or request.files.get("excel")
    if not upload or not upload.filename:
        return jsonify({"ok": False, "error": "Seleccioná un archivo Excel."}), 400
    name = upload.filename.lower()
    if not (name.endswith(".xlsx") or name.endswith(".xlsm")):
        return jsonify(
            {
                "ok": False,
                "error": "Solo se aceptan archivos Excel .xlsx o .xlsm.",
            }
        ), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            upload.save(tmp)
            tmp_path = tmp.name
        result = import_planilla(tmp_path, db.session, user_id=current_user.id)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    partes = [
        f"{result['unidades']} unidades",
        f"{result['asignadas']} asignadas",
        f"{result['destinos']} destinos",
    ]
    if result.get("sin_asignar"):
        partes.append(f"{result['sin_asignar']} sin destino")
    return jsonify(
        {
            "ok": True,
            "mensaje": "Importación exitosa. " + " · ".join(partes),
            "detalle": result,
        }
    )
