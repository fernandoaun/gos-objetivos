from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from gos.modulos.objetivos.services import reportes_service

bp = Blueprint("objetivos_dashboard", __name__)


@bp.route("/")
@login_required
def index():
    informe = reportes_service.generar_informe_cumplimiento(current_user.empresa_id)
    return render_template("dashboard/index.html", informe=informe)


@bp.route("/detalle/<filtro>")
@login_required
def detalle(filtro: str):
    if filtro not in reportes_service.DASHBOARD_FILTROS:
        abort(404)
    informe = reportes_service.generar_informe_cumplimiento(current_user.empresa_id)
    vista = reportes_service.preparar_vista_detalle(informe, filtro)
    return render_template(
        "dashboard/detalle.html",
        informe=informe,
        vista=vista,
    )
