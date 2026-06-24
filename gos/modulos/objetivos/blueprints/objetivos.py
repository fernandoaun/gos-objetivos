from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from gos.modulos.objetivos.models import Responsable
from gos.modulos.objetivos.models.objetivo import OBJETIVO_ESTADO_LABELS, OBJETIVO_ESTADOS
from gos.modulos.objetivos.services import objetivo_service
from gos.modulos.objetivos.utils.auth_decorators import requiere_rol

bp = Blueprint("objetivos_estrategicos", __name__)


def _empresa_id():
    return current_user.empresa_id


def _parse_fecha(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _catalogos():
    eid = _empresa_id()
    return {
        "responsables": Responsable.query.filter_by(empresa_id=eid, activo=True)
        .order_by(Responsable.nombre)
        .all(),
    }


def _render_index(edit_objetivo=None):
    cat = _catalogos()
    objetivos = objetivo_service.listar_objetivos(_empresa_id())
    return render_template(
        "objetivos/index.html",
        objetivos=objetivos,
        edit_objetivo=edit_objetivo,
        objetivo_estados=OBJETIVO_ESTADOS,
        objetivo_estado_labels=OBJETIVO_ESTADO_LABELS,
        responsables=cat["responsables"],
    )


@bp.route("/")
@login_required
def index():
    return _render_index()


@bp.route("/nuevo", methods=["POST"])
@login_required
@requiere_rol("administrador", "angel")
def nuevo():
    try:
        objetivo_service.crear_objetivo(
            empresa_id=_empresa_id(),
            nombre=request.form.get("nombre", ""),
            descripcion=request.form.get("descripcion", ""),
            responsable_texto=request.form.get("responsable_texto"),
            responsable_id=int(request.form["responsable_id"])
            if request.form.get("responsable_id")
            else None,
            fecha_inicio=_parse_fecha(request.form.get("fecha_inicio")),
            fecha_fin=_parse_fecha(request.form.get("fecha_fin")),
            estado=request.form.get("estado", "activo"),
        )
        flash("Objetivo estratégico agregado.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("objetivos_estrategicos.index"))


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@requiere_rol("administrador", "angel")
def editar(id):
    obj = objetivo_service.obtener_objetivo(_empresa_id(), id)
    if not obj:
        flash("Objetivo no encontrado.", "danger")
        return redirect(url_for("objetivos_estrategicos.index"))

    if request.method == "POST":
        try:
            objetivo_service.actualizar_objetivo(
                empresa_id=_empresa_id(),
                objetivo_id=id,
                nombre=request.form.get("nombre", ""),
                descripcion=request.form.get("descripcion", ""),
                responsable_texto=request.form.get("responsable_texto"),
                responsable_id=int(request.form["responsable_id"])
                if request.form.get("responsable_id")
                else None,
                fecha_inicio=_parse_fecha(request.form.get("fecha_inicio")),
                fecha_fin=_parse_fecha(request.form.get("fecha_fin")),
                estado=request.form.get("estado"),
                clear_responsable=not request.form.get("responsable_id"),
            )
            flash("Objetivo actualizado.", "success")
            return redirect(url_for("objetivos_estrategicos.index"))
        except ValueError as e:
            flash(str(e), "danger")

    return _render_index(edit_objetivo=obj)


@bp.route("/<int:id>/eliminar", methods=["POST"])
@login_required
@requiere_rol("administrador", "angel")
def eliminar(id):
    try:
        objetivo_service.eliminar_objetivo(_empresa_id(), id)
        flash("Objetivo eliminado.", "info")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("objetivos_estrategicos.index"))


@bp.route("/cargar-plantilla-2026", methods=["POST"])
@login_required
@requiere_rol("administrador", "angel")
def cargar_plantilla_2026():
    try:
        n = objetivo_service.cargar_plantilla_2026(_empresa_id())
        flash(f"Se cargaron {n} objetivos estratégicos 2026.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("objetivos_estrategicos.index"))
