from datetime import date

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from gos.modulos.capacitacion.models import Participante
from gos.modulos.capacitacion.services import (
    analitico_participante,
    encuentros_calendario,
    resumen_dashboard,
)

bp = Blueprint("capacitacion_api", __name__)


@bp.route("/participantes")
@login_required
def listar_participantes():
    q = Participante.query.filter_by(empresa_id=current_user.empresa_id, activo=True)
    sector_id = request.args.get("sector_id", type=int)
    puesto_id = request.args.get("puesto_id", type=int)
    if sector_id:
        q = q.filter_by(sector_id=sector_id)
    if puesto_id:
        q = q.filter_by(puesto_id=puesto_id)

    items = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "legajo": p.legajo,
            "sector_id": p.sector_id,
            "puesto_id": p.puesto_id,
        }
        for p in q.order_by(Participante.nombre).all()
    ]
    return jsonify({"participantes": items})


@bp.route("/participantes/<int:participante_id>/analitico")
@login_required
def analitico(participante_id: int):
    try:
        data = analitico_participante(participante_id, empresa_id=current_user.empresa_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 403
    return jsonify(data)


@bp.route("/dashboard")
@login_required
def dashboard():
    return jsonify(resumen_dashboard(current_user.empresa_id))


@bp.route("/encuentros")
@login_required
def listar_encuentros():
    desde_s = request.args.get("desde")
    hasta_s = request.args.get("hasta")
    hoy = date.today()
    try:
        desde = date.fromisoformat(desde_s) if desde_s else hoy.replace(day=1)
        hasta = date.fromisoformat(hasta_s) if hasta_s else hoy
    except ValueError:
        return jsonify({"error": "Fechas inválidas"}), 400
    items = encuentros_calendario(current_user.empresa_id, desde, hasta)
    return jsonify({"encuentros": items})
