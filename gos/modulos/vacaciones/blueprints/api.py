import os
import tempfile

from flask import Blueprint, jsonify, request
from flask_login import login_required

from gos.extensions import db
from gos.modulos.vacaciones.importer import import_excel
from gos.modulos.vacaciones.tot_hs_importer import import_tot_hs_excel
from gos.modulos.vacaciones import services

bp = Blueprint("vacaciones_api", __name__)


def _parse_anios_arg():
    raw_list = request.args.getlist("anios")
    parts = []
    for item in raw_list:
        parts.extend(item.replace(";", ",").split(","))
    years = []
    for part in parts:
        part = part.strip()
        if part.isdigit():
            years.append(int(part))
    return sorted(set(years)) or None


def _tot_hs_filters():
    return {
        "periodo": request.args.get("periodo") or None,
        "cliente": request.args.get("cliente") or request.args.get("sector") or None,
        "tipo_servicio": request.args.get("tipo_servicio") or None,
    }


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
            anios=_parse_anios_arg(),
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
            anios=_parse_anios_arg(),
        )
    )


@bp.route("/tot-hs/meta")
@login_required
def tot_hs_meta():
    return jsonify(services.get_tot_hs_meta(db.session))


@bp.route("/tot-hs/resumen")
@login_required
def tot_hs_resumen():
    return jsonify(services.get_tot_hs_resumen(db.session, **_tot_hs_filters()))


@bp.route("/tot-hs/por-mes")
@login_required
def tot_hs_por_mes():
    return jsonify(services.get_tot_hs_por_mes(db.session, **_tot_hs_filters()))


@bp.route("/tot-hs/por-sector")
@login_required
def tot_hs_por_sector():
    filters = _tot_hs_filters()
    filters.pop("cliente", None)
    return jsonify(services.get_tot_hs_por_sector(db.session, **filters))


@bp.route("/tot-hs/por-empleado")
@login_required
def tot_hs_por_empleado():
    return jsonify(services.get_tot_hs_por_empleado(db.session, **_tot_hs_filters()))


@bp.route("/tot-hs/detalle")
@login_required
def tot_hs_detalle():
    filters = _tot_hs_filters()
    empleado = request.args.get("empleado") or None
    try:
        limit = int(request.args.get("limit") or 500)
    except ValueError:
        limit = 500
    return jsonify(
        services.get_tot_hs_detalle(
            db.session, empleado=empleado, limit=limit, **filters
        )
    )


def _save_upload_and_import(import_fn):
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
        result = import_fn(tmp_path, db.session)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return result


@bp.route("/importar/excel", methods=["POST"])
@login_required
def importar_excel():
    outcome = _save_upload_and_import(import_excel)
    if isinstance(outcome, tuple):
        return outcome
    result = outcome

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


@bp.route("/importar/total", methods=["POST"])
@login_required
def importar_total():
    """Carga Tot Hs. por período: períodos viejos se conservan; el mismo rango se pisa."""
    outcome = _save_upload_and_import(import_tot_hs_excel)
    if isinstance(outcome, tuple):
        return outcome
    result = outcome

    partes = []
    if result["registros"] > 0:
        accion = "reemplazadas" if result.get("periodo_reemplazado") else "nuevas"
        label = result.get("periodo_label") or (
            f"{result.get('fecha_min')} → {result.get('fecha_max')}"
        )
        partes.append(
            f"{result['registros']} filas {accion} · período {label} · "
            f"{result.get('personas', 0)} personas"
        )

    return jsonify(
        {
            "ok": True,
            "mensaje": "Tot Hs. actualizado. " + " | ".join(partes)
            if partes
            else "Importación exitosa sin filas de horas.",
            "detalle": result,
        }
    )
