from datetime import datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from io import BytesIO

from app.models import Area, Responsable
from app.models.foda import FODA_LABELS, FODA_TIPOS
from app.services import foda_service
from app.services.foda_dafo_service import (
    generar_matriz_dafo,
    guardar_tarea_cuadrante,
    total_estrategias_dafo,
)
from app.services.foda_pdf_export import generar_pdf_foda
from app.utils.auth_decorators import requiere_rol

bp = Blueprint("foda", __name__)


def _empresa_id():
    return current_user.empresa_id


def _catalogos():
    eid = _empresa_id()
    return {
        "areas": Area.query.filter_by(empresa_id=eid).order_by(Area.nombre).all(),
        "responsables": Responsable.query.filter_by(empresa_id=eid, activo=True)
        .order_by(Responsable.nombre)
        .all(),
    }


def _parse_fecha(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _render_index(edit_item=None):
    empresa_id = _empresa_id()
    matriz = foda_service.obtener_matriz(empresa_id)
    documento = foda_service.ultimo_documento(empresa_id)
    total = sum(len(v) for v in matriz.values())
    dafo = None
    total_dafo = 0
    dafo_error = None
    if total > 0:
        try:
            dafo = generar_matriz_dafo(matriz, empresa_id=empresa_id)
            total_dafo = total_estrategias_dafo(dafo)
        except Exception as exc:
            current_app.logger.exception("Error generando DAFO")
            dafo_error = str(exc)
    cat = _catalogos()
    return render_template(
        "foda/index.html",
        matriz=matriz,
        dafo=dafo,
        total_dafo=total_dafo,
        dafo_error=dafo_error,
        documento=documento,
        total=total,
        foda_labels=FODA_LABELS,
        foda_tipos=FODA_TIPOS,
        edit_item=edit_item,
        areas=cat["areas"],
        responsables=cat["responsables"],
    )


@bp.route("/")
@login_required
def index():
    return _render_index()


@bp.route("/importar", methods=["POST"])
@login_required
def importar():
    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename:
        flash("Seleccioná un archivo Word (.docx).", "warning")
        return redirect(url_for("foda.index"))

    try:
        doc = foda_service.importar_word(
            empresa_id=_empresa_id(),
            file_storage=archivo,
            usuario_nombre=current_user.nombre,
            reemplazar=request.form.get("reemplazar") == "1",
        )
        flash(
            f"FODA importado: {doc.total_items} ítems desde «{doc.nombre_archivo}».",
            "success",
        )
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash(
            "No se pudo leer el archivo. Verificá que sea .docx y que tenga secciones "
            "Fortalezas, Oportunidades, Debilidades y Amenazas.",
            "danger",
        )

    return redirect(url_for("foda.index"))


@bp.route("/item/nuevo", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente", "responsable")
def item_nuevo():
    try:
        foda_service.crear_item_manual(
            empresa_id=_empresa_id(),
            tipo=request.form.get("tipo", "F"),
            descripcion=request.form.get("descripcion", ""),
            area_id=int(request.form["area_id"]) if request.form.get("area_id") else None,
            responsable_id=int(request.form["responsable_id"])
            if request.form.get("responsable_id")
            else None,
            fecha=_parse_fecha(request.form.get("fecha")),
        )
        flash("Ítem FODA agregado.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("foda.index"))


@bp.route("/item/<int:id>/editar", methods=["GET", "POST"])
@login_required
@requiere_rol("admin", "gerente", "responsable")
def item_editar(id):
    item = foda_service.obtener_item(_empresa_id(), id)
    if not item:
        flash("Ítem no encontrado.", "danger")
        return redirect(url_for("foda.index"))

    if request.method == "POST":
        try:
            foda_service.actualizar_item(
                empresa_id=_empresa_id(),
                item_id=id,
                descripcion=request.form.get("descripcion", ""),
                tipo=request.form.get("tipo"),
                area_id=int(request.form["area_id"]) if request.form.get("area_id") else None,
                responsable_id=int(request.form["responsable_id"])
                if request.form.get("responsable_id")
                else None,
                fecha=_parse_fecha(request.form.get("fecha")),
                clear_area=not request.form.get("area_id"),
                clear_responsable=not request.form.get("responsable_id"),
            )
            flash("Ítem actualizado.", "success")
            return redirect(url_for("foda.index"))
        except ValueError as e:
            flash(str(e), "danger")

    return _render_index(edit_item=item)


@bp.route("/item/<int:id>/eliminar", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente")
def item_eliminar(id):
    try:
        foda_service.eliminar_item(_empresa_id(), id)
        flash("Ítem eliminado.", "info")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("foda.index"))


@bp.route("/dafo/tarea", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente", "responsable")
def dafo_guardar_tarea():
    payload = request.get_json(silent=True) or {}
    tipo = (payload.get("tipo") or request.form.get("tipo") or "").strip().upper()
    origen_a = (payload.get("origen_a_codigo") or request.form.get("origen_a_codigo") or "").strip()
    origen_b = (payload.get("origen_b_codigo") or request.form.get("origen_b_codigo") or "").strip()
    tarea = payload.get("tarea") if payload else request.form.get("tarea", "")
    _ = origen_a, origen_b

    wants_json = (
        request.get_json(silent=True) is not None
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    try:
        guardar_tarea_cuadrante(_empresa_id(), tipo, tarea)
        if wants_json:
            return jsonify({"ok": True})
        flash("Tarea DAFO guardada.", "success")
    except ValueError as e:
        if wants_json:
            return jsonify({"ok": False, "error": str(e)}), 400
        flash(str(e), "danger")

    return redirect(url_for("foda.index") + "#matriz-dafo")


@bp.route("/exportar.pdf")
@login_required
def exportar_pdf():
    matriz = foda_service.obtener_matriz(_empresa_id())
    total = sum(len(v) for v in matriz.values())
    if total == 0:
        flash("No hay ítems FODA para exportar.", "warning")
        return redirect(url_for("foda.index"))

    nombre_empresa = current_user.empresa.nombre if current_user.empresa else "Empresa"
    try:
        pdf_bytes = generar_pdf_foda(nombre_empresa, matriz)
    except Exception:
        current_app.logger.exception("Error generando PDF FODA")
        flash("No se pudo generar el PDF. Intentá de nuevo.", "danger")
        return redirect(url_for("foda.index"))

    filename = f"FODA_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
