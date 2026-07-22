import os
import tempfile

from flask import Blueprint, jsonify, request
from flask_login import login_required

from gos.extensions import db
from gos.modulos.mantenimiento import services
from gos.modulos.mantenimiento.importer import import_vtv_excel

bp = Blueprint("mantenimiento_api", __name__)


@bp.route("/health")
@login_required
def health():
    return jsonify({"ok": True, "ts": int(__import__("time").time() * 1000)})


@bp.route("/meta")
@login_required
def meta():
    return jsonify(services.get_meta(db.session))


@bp.route("/plan")
@login_required
def plan():
    anio_raw = request.args.get("anio")
    anio = int(anio_raw) if anio_raw and anio_raw.isdigit() else None
    return jsonify(services.get_plan(db.session, anio=anio))


@bp.route("/vtv")
@login_required
def vtv():
    return jsonify(services.get_vtv(db.session))


@bp.route("/importar/excel", methods=["POST"])
@login_required
def importar_excel():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"error": "No se recibió archivo"}), 400
    if not upload.filename.lower().endswith((".xlsx", ".xlsm")):
        return jsonify(
            {
                "error": "Solo se aceptan archivos Excel .xlsx o .xlsm. "
                "Si tenés un .xls antiguo, abrilo en Excel y guardalo como .xlsx."
            }
        ), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            upload.save(tmp)
            tmp_path = tmp.name
        result = import_vtv_excel(tmp_path, db.session)
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    partes = []
    if result.get("anio"):
        partes.append(f"Plan {result['anio']}")
    if result.get("unidades_plan"):
        partes.append(f"{result['unidades_plan']} unidades")
    if result.get("celdas"):
        partes.append(f"{result['celdas']} celdas R/P/E")
    if result.get("vtv"):
        partes.append(f"{result['vtv']} vencimientos VTV")

    return jsonify(
        {
            "ok": True,
            "mensaje": "Importación exitosa. " + " · ".join(partes)
            if partes
            else "Importación exitosa sin datos.",
            "detalle": result,
        }
    )
