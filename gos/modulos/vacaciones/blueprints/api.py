import os
import tempfile

from flask import Blueprint, jsonify, request
from flask_login import login_required

from gos.modulos.vacaciones.database import get_session
from gos.modulos.vacaciones.importer import import_excel
from gos.modulos.vacaciones import services

bp = Blueprint("vacaciones_api", __name__)


def _db():
    return get_session()


@bp.route("/health")
@login_required
def health():
    return jsonify({"ok": True, "ts": int(__import__("time").time() * 1000)})


@bp.route("/dashboard/años")
@login_required
def dashboard_anios():
    db = _db()
    try:
        return jsonify(services.get_anios(db))
    finally:
        db.close()


@bp.route("/dashboard/sectores")
@login_required
def dashboard_sectores():
    db = _db()
    try:
        return jsonify(services.get_sectores(db))
    finally:
        db.close()


@bp.route("/dashboard/empleados")
@login_required
def dashboard_empleados():
    db = _db()
    try:
        sector = request.args.get("sector")
        return jsonify(services.get_empleados(db, sector=sector or None))
    finally:
        db.close()


@bp.route("/vacaciones/deuda")
@login_required
def vacaciones_deuda():
    db = _db()
    try:
        return jsonify(
            services.get_deuda_vacaciones(
                db,
                desde=request.args.get("desde"),
                hasta=request.args.get("hasta"),
                sector=request.args.get("sector"),
            )
        )
    finally:
        db.close()


@bp.route("/vacaciones/resumen-por-sector")
@login_required
def vacaciones_resumen_sector():
    db = _db()
    try:
        return jsonify(
            services.get_resumen_sector(
                db,
                desde=request.args.get("desde"),
                hasta=request.args.get("hasta"),
            )
        )
    finally:
        db.close()


@bp.route("/importar/excel", methods=["POST"])
@login_required
def importar_excel():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"error": "No se recibió archivo"}), 400
    if not upload.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify({"error": "Solo se aceptan archivos Excel (.xlsx, .xls)"}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        upload.save(tmp.name)
        tmp_path = tmp.name

    db = _db()
    try:
        result = import_excel(tmp_path, db)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        os.unlink(tmp_path)
        db.close()

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
