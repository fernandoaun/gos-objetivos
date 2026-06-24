from datetime import datetime

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from gos.modulos.objetivos.services import reportes_service

bp = Blueprint("objetivos_reportes", __name__)


@bp.route("/")
@login_required
def index():
    informe = reportes_service.generar_informe_cumplimiento(current_user.empresa_id)
    return render_template(
        "reportes/index.html",
        informe=informe,
        fecha_informe=datetime.now(),
    )
