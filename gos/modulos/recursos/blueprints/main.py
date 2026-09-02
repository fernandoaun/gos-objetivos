from flask import Blueprint, render_template, request
from flask_login import login_required

from gos.modulos.recursos import services
from gos.modulos.recursos.models import TIPOS_UNIDAD, TIPO_LABELS

bp = Blueprint("recursos_main", __name__)


@bp.route("/")
@login_required
def index():
    data = services.resumen()
    return render_template(
        "recursos/index.html",
        resumen=data,
        detalle=services.detalle_tablero(data),
        historial=services.listar_cambios(),
    )


@bp.route("/flota")
@login_required
def flota():
    q = (request.args.get("q") or "").strip()
    tipo = (request.args.get("tipo") or "").strip().upper()
    grupo = (request.args.get("grupo") or "").strip().lower()
    dest_raw = (request.args.get("destino") or "").strip()
    sin_asignar = dest_raw == "none"
    destino_id = int(dest_raw) if dest_raw.isdigit() else None
    incluir_bajas = request.args.get("bajas") == "1"
    unidades = services.listar_unidades(
        q=q or None,
        tipo=tipo or None,
        grupo=grupo or None,
        destino_id=destino_id,
        sin_asignar=sin_asignar,
        activos=None if incluir_bajas else True,
    )
    return render_template(
        "recursos/flota.html",
        unidades=[services.unidad_dict(u) for u in unidades],
        destinos=services.destinos_payload(),
        tipos=TIPOS_UNIDAD,
        tipo_labels=TIPO_LABELS,
        filtros={
            "q": q,
            "tipo": tipo,
            "grupo": grupo,
            "destino": dest_raw,
            "bajas": incluir_bajas,
        },
    )


@bp.route("/servicios")
@login_required
def servicios():
    return render_template(
        "recursos/servicios.html",
        resumen=services.resumen(),
        tipos=TIPOS_UNIDAD,
        tipo_labels=TIPO_LABELS,
    )


@bp.route("/centros")
@login_required
def centros():
    incluir_bajas = request.args.get("bajas") == "1"
    servicios = [d for d in services.destinos_payload() if d["grupo"] == "servicio"]
    return render_template(
        "recursos/centros.html",
        centros=services.centros_payload(activos=None if incluir_bajas else True),
        servicios=servicios,
        filtros={"bajas": incluir_bajas},
    )


@bp.route("/importar")
@login_required
def importar():
    return render_template("recursos/importar.html")
