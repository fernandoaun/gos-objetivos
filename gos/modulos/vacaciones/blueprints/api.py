import os
import tempfile

from flask import Blueprint, jsonify, request
from flask_login import login_required

from gos.extensions import db
from gos.modulos.vacaciones.importer import import_excel
from gos.modulos.vacaciones import services

bp = Blueprint("vacaciones_api", __name__)


@bp.route("/health")
@login_required
def health():
    return jsonify({"ok": True, "ts": int(__import__("time").time() * 1000)})


@bp.route("/dashboard/años")
@login_required
def dashboard_anios():
    return jsonify(services.get_anios(db.session))


@bp.route("/dashboard/sectores")
@login_required
def dashboard_sectores():
    return jsonify(services.get_sectores(db.session))


@bp.route("/dashboard/empleados")
@login_required
def dashboard_empleados():
    sector = request.args.get("sector")
    return jsonify(services.get_empleados(db.session, sector=sector or None))


@bp.route("/vacaciones/deuda")
@login_required
def vacaciones_deuda():
    return jsonify(
        services.get_deuda_vacaciones(
            db.session,
            desde=request.args.get("desde"),
            hasta=request.args.get("hasta"),
            sector=request.args.get("sector"),
        )
    )


@bp.route("/vacaciones/resumen-por-sector")
@login_required
def vacaciones_resumen_sector():
    return jsonify(
        services.get_resumen_sector(
            db.session,
            desde=request.args.get("desde"),
            hasta=request.args.get("hasta"),
        )
    )


@bp.route("/importar/excel", methods=["POST"])
@login_required
def importar_excel():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"error": "No se recibió archivo"}), 400
    if not upload.filename.lower().endswith((".xlsx", ".xls", ".xlsm")):
        return jsonify({"error": "Solo se aceptan archivos Excel (.xlsx, .xls)"}), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            upload.save(tmp)
            tmp_path = tmp.name

        result = import_excel(tmp_path, db.session)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    partes = []
    if result["registros"] > 0:
        partes.append(
            f"Registros: {result['registros']} procesados "
            f"({result['registros_nuevos']} nuevos, {result['registros_actualizados']} actualizados)"
        )
    if result["vacaciones"] > 0:
        partes.append(
            f"Vacaciones: {result['vacaciones']} procesadas "
            f"({result['vacaciones_nuevas']} nuevas, {result['vacaciones_actualizadas']} actualizadas)"
        )

    return jsonify(
        {
            "ok": True,
            "mensaje": "Importación exitosa. " + " | ".join(partes)
            if partes
            else "Importación exitosa sin datos.",
            "detalle": result,
        }
    )
