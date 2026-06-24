from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from gos.modulos.objetivos.models.kpi import (
    KPI_TIPO_MEDICION_LABELS,
    KPI_TIPO_MEDICION_OPCIONES,
    KPI_TIPO_MEDICION_TITULOS,
    MESES_KPI,
    MESES_KPI_LABELS,
)
from gos.modulos.objetivos.services import kpi_service
from gos.modulos.objetivos.utils.auth_decorators import requiere_rol

bp = Blueprint("objetivos_kpis", __name__)


def _empresa_id():
    return current_user.empresa_id


def _puede_editar_kpi() -> bool:
    return current_user.rol in ("admin", "gerente", "responsable")


def _format_valor_mes(valor):
    if valor is None or valor == "":
        return ""
    try:
        num = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if num == int(num):
        return str(int(num))
    return f"{num:g}"


def _valores_mes_form():
    return {str(m): request.form.get(f"mes_{m}") for m in MESES_KPI}


def _render_index(
    edit_id: int | None = None,
    ver_id: int | None = None,
):
    empresa_id = _empresa_id()
    kpi_service.limpiar_etiquetas_grupo(empresa_id)
    return render_template(
        "kpis/index.html",
        filas=kpi_service.listar_kpis_con_metricas(empresa_id),
        meses=MESES_KPI,
        meses_labels=MESES_KPI_LABELS,
        tipo_medicion_opciones=KPI_TIPO_MEDICION_OPCIONES,
        tipo_medicion_labels=KPI_TIPO_MEDICION_LABELS,
        tipo_medicion_titulos=KPI_TIPO_MEDICION_TITULOS,
        siguiente_numero=kpi_service.siguiente_numero_kpi(empresa_id),
        excel_path=kpi_service.excel_path(),
        kpi_valor_mes=_format_valor_mes,
        kpi_editable=_puede_editar_kpi(),
        edit_id=edit_id,
        ver_id=ver_id,
    )


@bp.route("/")
@login_required
def index():
    return _render_index(
        edit_id=request.args.get("edit", type=int),
        ver_id=request.args.get("ver", type=int),
    )


@bp.route("/importar-excel", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente", "responsable")
def importar_excel():
    reemplazar = request.form.get("reemplazar") == "1"
    try:
        n = kpi_service.importar_desde_excel(_empresa_id(), reemplazar=reemplazar)
        flash(f"Se importaron {n} KPI desde Excel.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("objetivos_kpis.index"))


@bp.route("/nuevo", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente", "responsable")
def nuevo():
    try:
        kpi_service.crear_kpi(
            _empresa_id(),
            codigo=request.form.get("codigo", ""),
            indicador=request.form.get("indicador", ""),
            responsable=request.form.get("responsable"),
            medio=request.form.get("medio"),
            resultado_2025=request.form.get("resultado_2025"),
            meta_2026=request.form.get("meta_2026"),
            tipo_agregacion=request.form.get("tipo_agregacion"),
            observacion=request.form.get("observacion"),
            valores_mes=_valores_mes_form(),
        )
        flash("KPI agregado.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("objetivos_kpis.index", nuevo=1))
    return redirect(url_for("objetivos_kpis.index"))


@bp.route("/<int:id>/actualizar", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente", "responsable")
def actualizar(id):
    try:
        kpi = kpi_service.actualizar_kpi(
            _empresa_id(),
            id,
            indicador=request.form.get("indicador"),
            responsable=request.form.get("responsable"),
            medio=request.form.get("medio"),
            resultado_2025=request.form.get("resultado_2025"),
            meta_2026=request.form.get("meta_2026"),
            tipo_agregacion=request.form.get("tipo_agregacion"),
            observacion=request.form.get("observacion"),
            valores_mes=_valores_mes_form(),
        )
        flash(f"{kpi.codigo} guardado.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("objetivos_kpis.index", edit=id))
    return redirect(url_for("objetivos_kpis.index"))


@bp.route("/<int:id>/tipo", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente", "responsable")
def actualizar_tipo(id):
    try:
        kpi = kpi_service.actualizar_kpi(
            _empresa_id(),
            id,
            tipo_agregacion=request.form.get("tipo_agregacion"),
        )
        flash(f"Tipo de {kpi.codigo} actualizado.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("objetivos_kpis.index", ver=id))


@bp.route("/<int:id>/eliminar", methods=["POST"])
@login_required
@requiere_rol("admin", "gerente", "responsable")
def eliminar(id):
    try:
        codigo = kpi_service.eliminar_kpi(_empresa_id(), id)
        flash(f"{codigo} eliminado.", "info")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("objetivos_kpis.index"))
