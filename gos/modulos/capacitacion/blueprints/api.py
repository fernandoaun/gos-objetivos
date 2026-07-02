from datetime import date
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user, login_required

from gos.models import Empresa
from gos.models.usuario import usuario_cumple_rol
from gos.modulos.capacitacion.models import Participante
from gos.modulos.capacitacion.services import (
    actualizar_curso,
    actualizar_encuentro,
    actualizar_participante,
    obtener_participante,
    actualizar_puesto,
    actualizar_sector,
    analitico_participante,
    baja_curso,
    baja_participante,
    busqueda_global,
    crear_curso,
    crear_empresa_capacitadora,
    crear_encuentro,
    crear_instructor,
    crear_participante,
    crear_programa,
    crear_puesto,
    crear_requisito,
    crear_sector,
    descargar_certificado_registro,
    descargar_documento_certificacion,
    descargar_foto_participante,
    detalle_encuentro,
    eliminar_certificado_registro,
    eliminar_encuentro,
    eliminar_foto_participante,
    eliminar_requisito,
    encuentros_cronograma,
    enviar_notificaciones_alertas,
    generar_alertas,
    guardar_config,
    importar_cursos_excel,
    importar_participantes_excel,
    inscribir_participantes,
    listar_alertas,
    listar_cursos,
    listar_empresas_capacitadoras,
    listar_instructores,
    listar_programas,
    listar_participantes_por_puestos,
    listar_puestos,
    listar_requisitos,
    listar_sectores,
    marcar_alerta_leida,
    matriz_capacitaciones,
    obtener_config,
    obtener_taxonomia_cursos,
    participantes_encuentro,
    registrar_asistencias,
    reporte_iso,
    resumen_dashboard,
    sincronizar_legajos_vacaciones,
    subir_certificado_registro,
    subir_documento_certificacion,
    subir_foto_participante,
)
from gos.modulos.capacitacion.services.taxonomia_service import (
    actualizar_taxonomia_item,
    baja_taxonomia_item,
    crear_taxonomia_item,
    listar_taxonomia_items,
)
from gos.modulos.capacitacion.services.export_service import exportar_matriz_excel
from gos.modulos.capacitacion.services.pdf_export_service import (
    generar_pdf_general,
    generar_pdf_iso,
    generar_pdf_participante,
)

bp = Blueprint("capacitacion_api", __name__)


def _puede_editar() -> bool:
    return usuario_cumple_rol(current_user, "administrador", "angel")


def _json_body() -> dict:
    return request.get_json(silent=True) or {}


def _parse_id_list(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(x) for x in raw.split(",") if x.strip().isdigit()]


def _empresa_nombre() -> str:
    emp = Empresa.query.get(current_user.empresa_id)
    return emp.nombre if emp else "Empresa"


@bp.route("/configuracion", methods=["GET", "PUT"])
@login_required
def configuracion():
    if request.method == "GET":
        return jsonify({"config": obtener_config(current_user.empresa_id)})
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    try:
        cfg = guardar_config(current_user.empresa_id, _json_body())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"config": cfg})


@bp.route("/busqueda")
@login_required
def busqueda():
    q = request.args.get("q", "")
    return jsonify(busqueda_global(current_user.empresa_id, q))


@bp.route("/participantes", methods=["GET", "POST"])
@login_required
def participantes():
    if request.method == "POST":
        if not _puede_editar():
            return jsonify({"error": "No tenés permiso para esta acción."}), 403
        try:
            item = crear_participante(current_user.empresa_id, _json_body())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"participante": item}), 201

    q = Participante.query.filter_by(empresa_id=current_user.empresa_id)
    if request.args.get("activo", "true").lower() != "all":
        q = q.filter_by(activo=request.args.get("activo", "true").lower() == "true")
    sector_id = request.args.get("sector_id", type=int)
    puesto_id = request.args.get("puesto_id", type=int)
    puesto_ids = _parse_id_list(request.args.get("puesto_ids"))
    busqueda = (request.args.get("q") or "").strip().lower()
    if puesto_ids:
        items = listar_participantes_por_puestos(current_user.empresa_id, puesto_ids)
        if busqueda:
            items = [
                p
                for p in items
                if busqueda in p["nombre"].lower() or busqueda in (p.get("legajo") or "").lower()
            ]
        return jsonify({"participantes": items})

    if sector_id:
        q = q.filter_by(sector_id=sector_id)
    if puesto_id:
        q = q.filter_by(puesto_id=puesto_id)

    items = []
    for p in q.order_by(Participante.nombre).all():
        if busqueda and busqueda not in p.nombre_completo.lower() and busqueda not in (p.legajo or "").lower():
            continue
        items.append(
            {
                "id": p.id,
                "nombre": p.nombre_completo,
                "legajo": p.legajo,
                "dni": p.dni,
                "tiene_foto": bool(p.foto_path),
                "sector_id": p.sector_id,
                "puesto_id": p.puesto_id,
                "activo": p.activo,
            }
        )
    return jsonify({"participantes": items})


@bp.route("/participantes/<int:participante_id>", methods=["GET", "PUT"])
@login_required
def participante_detalle(participante_id: int):
    if request.method == "GET":
        try:
            item = obtener_participante(current_user.empresa_id, participante_id)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        return jsonify({"participante": item})

    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    try:
        item = actualizar_participante(current_user.empresa_id, participante_id, _json_body())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"participante": item})


@bp.route("/participantes/<int:participante_id>/foto", methods=["POST", "GET", "DELETE"])
@login_required
def foto_participante(participante_id: int):
    eid = current_user.empresa_id
    if request.method == "GET":
        try:
            path, mimetype = descargar_foto_participante(eid, participante_id)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        return send_file(path, mimetype=mimetype)
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    if request.method == "DELETE":
        try:
            return jsonify(eliminar_foto_participante(eid, participante_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    archivo = request.files.get("archivo")
    try:
        item = subir_foto_participante(eid, participante_id, archivo)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"participante": item})


@bp.route("/participantes/<int:participante_id>/analitico")
@login_required
def analitico(participante_id: int):
    try:
        data = analitico_participante(participante_id, empresa_id=current_user.empresa_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 403
    return jsonify(data)


@bp.route("/cursos/taxonomia")
@login_required
def cursos_taxonomia():
    return jsonify(obtener_taxonomia_cursos(current_user.empresa_id))


@bp.route("/taxonomia/items", methods=["GET", "POST"])
@login_required
def taxonomia_items():
    eid = current_user.empresa_id
    if request.method == "POST":
        if not _puede_editar():
            return jsonify({"error": "No tenés permiso para esta acción."}), 403
        try:
            item = crear_taxonomia_item(eid, _json_body())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"item": item}), 201
    return jsonify(
        {
            "items": listar_taxonomia_items(
                eid,
                nivel=request.args.get("nivel"),
                parent_id=request.args.get("parent_id", type=int),
            )
        }
    )


@bp.route("/taxonomia/items/<int:item_id>", methods=["PUT", "DELETE"])
@login_required
def taxonomia_item_detalle(item_id: int):
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    eid = current_user.empresa_id
    if request.method == "DELETE":
        try:
            return jsonify(baja_taxonomia_item(eid, item_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    try:
        item = actualizar_taxonomia_item(eid, item_id, _json_body())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"item": item})


@bp.route("/cursos", methods=["GET", "POST"])
@login_required
def cursos():
    if request.method == "POST":
        if not _puede_editar():
            return jsonify({"error": "No tenés permiso para esta acción."}), 403
        try:
            item = crear_curso(current_user.empresa_id, _json_body())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"curso": item}), 201
    return jsonify({"cursos": listar_cursos(current_user.empresa_id)})


@bp.route("/cursos/<int:curso_id>", methods=["PUT", "DELETE"])
@login_required
def curso_detalle(curso_id: int):
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    if request.method == "DELETE":
        try:
            return jsonify(baja_curso(current_user.empresa_id, curso_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    try:
        item = actualizar_curso(current_user.empresa_id, curso_id, _json_body())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"curso": item})


@bp.route("/cursos/importar", methods=["POST"])
@login_required
def importar_cursos():
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"error": "Debe enviar un archivo Excel."}), 400
    try:
        result = importar_cursos_excel(current_user.empresa_id, archivo.read())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route("/participantes/importar", methods=["POST"])
@login_required
def importar_participantes():
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"error": "Debe enviar un archivo Excel."}), 400
    try:
        result = importar_participantes_excel(current_user.empresa_id, archivo.read())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route("/participantes/<int:participante_id>", methods=["DELETE"])
@login_required
def baja_participante_route(participante_id: int):
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    try:
        return jsonify(baja_participante(current_user.empresa_id, participante_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/requisitos", methods=["GET", "POST"])
@login_required
def requisitos():
    if request.method == "POST":
        if not _puede_editar():
            return jsonify({"error": "No tenés permiso para esta acción."}), 403
        try:
            item = crear_requisito(current_user.empresa_id, _json_body())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"requisito": item}), 201
    return jsonify(
        {
            "requisitos": listar_requisitos(
                current_user.empresa_id,
                puesto_id=request.args.get("puesto_id", type=int),
                puesto_ids=_parse_id_list(request.args.get("puesto_ids")) or None,
                sector_id=request.args.get("sector_id", type=int),
                participante_id=request.args.get("participante_id", type=int),
            )
        }
    )


@bp.route("/requisitos/<int:requisito_id>", methods=["DELETE"])
@login_required
def eliminar_requisito_route(requisito_id: int):
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    try:
        eliminar_requisito(current_user.empresa_id, requisito_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@bp.route("/puestos", methods=["GET", "POST"])
@login_required
def puestos():
    if request.method == "POST":
        if not _puede_editar():
            return jsonify({"error": "No tenés permiso para esta acción."}), 403
        try:
            item = crear_puesto(current_user.empresa_id, _json_body())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"puesto": item}), 201
    return jsonify({"puestos": listar_puestos(current_user.empresa_id)})


@bp.route("/puestos/<int:puesto_id>", methods=["PUT"])
@login_required
def actualizar_puesto_route(puesto_id: int):
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    try:
        item = actualizar_puesto(current_user.empresa_id, puesto_id, _json_body())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"puesto": item})


@bp.route("/instructores", methods=["GET", "POST"])
@login_required
def instructores():
    if request.method == "POST":
        if not _puede_editar():
            return jsonify({"error": "No tenés permiso para esta acción."}), 403
        try:
            item = crear_instructor(current_user.empresa_id, _json_body())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"instructor": item}), 201
    return jsonify({"instructores": listar_instructores(current_user.empresa_id)})


@bp.route("/empresas-capacitadoras", methods=["GET", "POST"])
@login_required
def empresas_capacitadoras():
    if request.method == "POST":
        if not _puede_editar():
            return jsonify({"error": "No tenés permiso para esta acción."}), 403
        try:
            item = crear_empresa_capacitadora(current_user.empresa_id, _json_body())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"empresa_capacitadora": item}), 201
    return jsonify({"empresas_capacitadoras": listar_empresas_capacitadoras(current_user.empresa_id)})


@bp.route("/sectores", methods=["GET", "POST"])
@login_required
def sectores():
    if request.method == "POST":
        if not _puede_editar():
            return jsonify({"error": "No tenés permiso para esta acción."}), 403
        try:
            item = crear_sector(current_user.empresa_id, _json_body())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"sector": item}), 201
    return jsonify({"sectores": listar_sectores(current_user.empresa_id)})


@bp.route("/sectores/<int:sector_id>", methods=["PUT"])
@login_required
def actualizar_sector_route(sector_id: int):
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    try:
        item = actualizar_sector(current_user.empresa_id, sector_id, _json_body())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"sector": item})


@bp.route("/dashboard")
@login_required
def dashboard():
    sector_id = request.args.get("sector_id", type=int)
    return jsonify(resumen_dashboard(current_user.empresa_id, sector_id=sector_id))


@bp.route("/matriz")
@login_required
def matriz():
    return jsonify(
        matriz_capacitaciones(
            current_user.empresa_id,
            sector_id=request.args.get("sector_id", type=int),
            puesto_id=request.args.get("puesto_id", type=int),
            curso_id=request.args.get("curso_id", type=int),
            participante_id=request.args.get("participante_id", type=int),
            estado=request.args.get("estado"),
            solo_requeridos=request.args.get("solo_requeridos", "true").lower() != "false",
        )
    )


@bp.route("/matriz/exportar.xlsx")
@login_required
def exportar_matriz():
    buf = exportar_matriz_excel(
        current_user.empresa_id,
        sector_id=request.args.get("sector_id", type=int),
        puesto_id=request.args.get("puesto_id", type=int),
    )
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="matriz_capacitaciones.xlsx",
    )


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
    items = encuentros_cronograma(current_user.empresa_id, desde, hasta)
    return jsonify({"encuentros": items})


@bp.route("/encuentros", methods=["POST"])
@login_required
def crear_encuentro_route():
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    try:
        item = crear_encuentro(current_user.empresa_id, _json_body())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"encuentro": item}), 201


@bp.route("/encuentros/<int:encuentro_id>/participantes")
@login_required
def encuentro_participantes(encuentro_id: int):
    try:
        items = participantes_encuentro(current_user.empresa_id, encuentro_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"participantes": items})


@bp.route("/encuentros/<int:encuentro_id>", methods=["GET", "PUT", "DELETE"])
@login_required
def encuentro_detalle(encuentro_id: int):
    if request.method == "GET":
        try:
            return jsonify(detalle_encuentro(current_user.empresa_id, encuentro_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    if request.method == "DELETE":
        try:
            return jsonify(eliminar_encuentro(current_user.empresa_id, encuentro_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
    try:
        item = actualizar_encuentro(current_user.empresa_id, encuentro_id, _json_body())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"encuentro": item})


@bp.route("/encuentros/<int:encuentro_id>/asistencias", methods=["POST"])
@login_required
def asistencias_encuentro(encuentro_id: int):
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    body = _json_body()
    registros = body.get("asistencias") or []
    try:
        result = registrar_asistencias(current_user.empresa_id, encuentro_id, registros)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route("/programas", methods=["GET", "POST"])
@login_required
def programas():
    if request.method == "POST":
        if not _puede_editar():
            return jsonify({"error": "No tenés permiso para esta acción."}), 403
        try:
            item = crear_programa(current_user.empresa_id, _json_body())
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"programa": item}), 201
    return jsonify({
        "programas": listar_programas(
            current_user.empresa_id,
            puesto_id=request.args.get("puesto_id", type=int),
            participante_id=request.args.get("participante_id", type=int),
        )
    })


@bp.route("/programas/<int:programa_id>/inscripciones", methods=["POST"])
@login_required
def inscripciones(programa_id: int):
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    ids = _json_body().get("participante_ids") or []
    try:
        result = inscribir_participantes(current_user.empresa_id, programa_id, ids)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route("/alertas")
@login_required
def alertas():
    solo_criticas = request.args.get("criticas") == "1"
    return jsonify({"alertas": listar_alertas(current_user.empresa_id, solo_criticas=solo_criticas)})


@bp.route("/alertas/generar", methods=["POST"])
@login_required
def alertas_generar():
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    body = _json_body()
    enviar = body.get("enviar_email")
    if enviar is not None:
        enviar = bool(enviar)
    result = generar_alertas(current_user.empresa_id, enviar_email=enviar)
    return jsonify({
        "generadas": result["generadas"],
        "notificacion": result.get("notificacion"),
        "alertas": listar_alertas(current_user.empresa_id),
    })


@bp.route("/alertas/notificar", methods=["POST"])
@login_required
def alertas_notificar():
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    result = enviar_notificaciones_alertas(current_user.empresa_id)
    return jsonify({"notificacion": result})


@bp.route("/alertas/<int:alerta_id>/leida", methods=["POST"])
@login_required
def alerta_leida(alerta_id: int):
    try:
        item = marcar_alerta_leida(current_user.empresa_id, alerta_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"alerta": item})


@bp.route("/registros/<int:registro_id>/certificado", methods=["POST", "GET", "DELETE"])
@login_required
def certificado_registro(registro_id: int):
    eid = current_user.empresa_id
    if request.method == "GET":
        try:
            path, name = descargar_certificado_registro(eid, registro_id)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        return send_file(path, mimetype="application/pdf", as_attachment=True, download_name=name)
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    if request.method == "DELETE":
        try:
            return jsonify(eliminar_certificado_registro(eid, registro_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    archivo = request.files.get("archivo")
    try:
        item = subir_certificado_registro(eid, registro_id, archivo)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"registro": item})


@bp.route("/certificaciones/<int:cert_id>/documento", methods=["POST", "GET"])
@login_required
def documento_certificacion(cert_id: int):
    eid = current_user.empresa_id
    if request.method == "GET":
        try:
            path, name = descargar_documento_certificacion(eid, cert_id)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 404
        return send_file(path, mimetype="application/pdf", as_attachment=True, download_name=name)
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    archivo = request.files.get("archivo")
    try:
        item = subir_documento_certificacion(eid, cert_id, archivo)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"certificacion": item})


@bp.route("/reportes/iso/<norma>")
@login_required
def reporte_iso_route(norma: str):
    try:
        data = reporte_iso(current_user.empresa_id, norma)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(data)


@bp.route("/reportes/iso/<norma>.pdf")
@login_required
def reporte_iso_pdf(norma: str):
    try:
        pdf = generar_pdf_iso(_empresa_nombre(), current_user.empresa_id, norma)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"auditoria_iso_{norma}.pdf",
    )


@bp.route("/participantes/<int:participante_id>/reporte.pdf")
@login_required
def reporte_participante_pdf(participante_id: int):
    try:
        pdf = generar_pdf_participante(_empresa_nombre(), participante_id, current_user.empresa_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 403
    return send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"capacitacion_persona_{participante_id}.pdf",
    )


@bp.route("/reportes/general.pdf")
@login_required
def reporte_general_pdf():
    pdf = generar_pdf_general(_empresa_nombre(), current_user.empresa_id)
    return send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="reporte_capacitaciones_general.pdf",
    )


@bp.route("/participantes/sincronizar-vacaciones", methods=["POST"])
@login_required
def sync_vacaciones():
    if not _puede_editar():
        return jsonify({"error": "No tenés permiso para esta acción."}), 403
    try:
        result = sincronizar_legajos_vacaciones(current_user.empresa_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)
