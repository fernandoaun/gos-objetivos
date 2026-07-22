import os
import tempfile
from datetime import date, datetime

from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required

from gos.extensions import db
from gos.modulos.mantenimiento import services
from gos.modulos.mantenimiento.importer import import_vtv_excel

bp = Blueprint("mantenimiento_api", __name__)


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    text = str(raw).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha inválida: {raw}")


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


@bp.route("/vtv/fechas")
@login_required
def vtv_fechas():
    try:
        cantidad = int(request.args.get("cantidad") or 24)
    except ValueError:
        cantidad = 24
    return jsonify(services.fechas_vtv_disponibles(cantidad=min(cantidad, 60)))


@bp.route("/vtv/programar", methods=["POST"])
@login_required
def vtv_programar():
    data = request.get_json(silent=True) or {}
    try:
        unidad_id = int(data.get("unidad_id"))
        fecha_vtv = _parse_date(data.get("fecha_vtv"))
        if not fecha_vtv:
            raise ValueError("Indicá la fecha de VTV.")
        turno = services.programar_vtv(
            db.session,
            unidad_id=unidad_id,
            fecha_vtv=fecha_vtv,
            observaciones=data.get("observaciones"),
        )
    except (TypeError, ValueError) as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True, "turno": turno})


@bp.route("/vtv/turnos/<int:turno_id>/cancelar", methods=["POST"])
@login_required
def vtv_cancelar(turno_id: int):
    try:
        turno = services.cancelar_turno(db.session, turno_id)
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "turno": turno})


@bp.route("/vtv/turnos/<int:turno_id>/realizar", methods=["POST"])
@login_required
def vtv_realizar(turno_id: int):
    # multipart o JSON
    if request.content_type and "multipart/form-data" in request.content_type:
        resultado = request.form.get("resultado")
        observaciones = request.form.get("observaciones")
        fecha_raw = request.form.get("fecha_realizada")
        file_storage = request.files.get("certificado")
    else:
        data = request.get_json(silent=True) or {}
        resultado = data.get("resultado")
        observaciones = data.get("observaciones")
        fecha_raw = data.get("fecha_realizada")
        file_storage = None

    try:
        fecha = _parse_date(fecha_raw) if fecha_raw else None
        out = services.registrar_resultado_vtv(
            db.session,
            turno_id=turno_id,
            resultado=resultado,
            fecha_realizada=fecha,
            observaciones=observaciones,
            file_storage=file_storage,
        )
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True, **out})


@bp.route("/vtv/turnos/<int:turno_id>/certificado", methods=["POST"])
@login_required
def vtv_certificado_subir(turno_id: int):
    file_storage = request.files.get("certificado") or request.files.get("file")
    try:
        turno = services.adjuntar_certificado(db.session, turno_id, file_storage)
    except ValueError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True, "turno": turno})


@bp.route("/vtv/turnos/<int:turno_id>/certificado", methods=["GET"])
@login_required
def vtv_certificado_bajar(turno_id: int):
    try:
        path, nombre = services.obtener_certificado(db.session, turno_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return send_file(path, as_attachment=True, download_name=nombre)


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
