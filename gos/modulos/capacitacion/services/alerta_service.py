from __future__ import annotations

from datetime import date, timedelta

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    AlertaCapacitacion,
    EncuentroCapacitacion,
    Participante,
    RegistroCapacitacion,
)
from gos.modulos.capacitacion.services.analitico_service import analitico_participante
from gos.modulos.capacitacion.services.config_service import (
    dias_encuentro_proximo,
    dias_proximo_vencer,
    obtener_config,
)
from gos.modulos.capacitacion.services.notificacion_service import enviar_notificaciones_alertas


def generar_alertas(empresa_id: int, *, enviar_email: bool | None = None) -> dict:
    """Regenera alertas automáticas. Opcionalmente envía notificaciones por email."""
    hoy = date.today()
    dias_proximo = dias_proximo_vencer(empresa_id)
    dias_encuentro = dias_encuentro_proximo(empresa_id)
    AlertaCapacitacion.query.filter_by(empresa_id=empresa_id, resuelta=False).delete()
    creadas = 0

    participantes = Participante.query.filter_by(empresa_id=empresa_id, activo=True).all()
    for p in participantes:
        data = analitico_participante(p.id, empresa_id=empresa_id)
        for pend in data["pendientes"]:
            if not pend.get("obligatorio"):
                continue
            db.session.add(
                AlertaCapacitacion(
                    empresa_id=empresa_id,
                    participante_id=p.id,
                    curso_id=pend.get("curso_id"),
                    tipo="pendiente_obligatorio",
                    nivel="critico",
                    titulo=f"Capacitación obligatoria pendiente: {pend.get('nombre')}",
                    mensaje=f"{p.nombre} debe completar {pend.get('codigo')} — {pend.get('nombre')}",
                )
            )
            creadas += 1

        for reg in RegistroCapacitacion.query.filter_by(participante_id=p.id, aprobado=True).all():
            if reg.vigente_hasta and reg.vigente_hasta < hoy:
                db.session.add(
                    AlertaCapacitacion(
                        empresa_id=empresa_id,
                        participante_id=p.id,
                        curso_id=reg.curso_id,
                        tipo="vencimiento",
                        nivel="critico",
                        titulo="Capacitación vencida",
                        mensaje=f"{p.nombre}: curso venció el {reg.vigente_hasta.isoformat()}",
                        fecha_referencia=reg.vigente_hasta,
                    )
                )
                creadas += 1
            elif reg.vigente_hasta and reg.vigente_hasta <= hoy + timedelta(days=dias_proximo):
                db.session.add(
                    AlertaCapacitacion(
                        empresa_id=empresa_id,
                        participante_id=p.id,
                        curso_id=reg.curso_id,
                        tipo="vencimiento",
                        nivel="advertencia",
                        titulo="Capacitación próxima a vencer",
                        mensaje=f"{p.nombre}: vence el {reg.vigente_hasta.isoformat()}",
                        fecha_referencia=reg.vigente_hasta,
                    )
                )
                creadas += 1

    limite = hoy + timedelta(days=dias_encuentro)
    encuentros = (
        EncuentroCapacitacion.query.filter_by(empresa_id=empresa_id, estado="programado")
        .filter(EncuentroCapacitacion.fecha >= hoy)
        .filter(EncuentroCapacitacion.fecha <= limite)
        .all()
    )
    for enc in encuentros:
        db.session.add(
            AlertaCapacitacion(
                empresa_id=empresa_id,
                encuentro_id=enc.id,
                curso_id=enc.curso_id,
                tipo="curso_proximo",
                nivel="info",
                titulo=f"Curso próximo: {enc.titulo}",
                mensaje=f"Programado para {enc.fecha.isoformat()}",
                fecha_referencia=enc.fecha,
            )
        )
        creadas += 1

    db.session.commit()

    notif = None
    cfg = obtener_config(empresa_id)
    debe_enviar = enviar_email if enviar_email is not None else cfg.get("notif_email_activo")
    if debe_enviar:
        notif = enviar_notificaciones_alertas(empresa_id)

    return {"generadas": creadas, "notificacion": notif}


def listar_alertas(empresa_id: int, *, solo_criticas: bool = False) -> list[dict]:
    q = AlertaCapacitacion.query.filter_by(empresa_id=empresa_id, resuelta=False)
    if solo_criticas:
        q = q.filter(AlertaCapacitacion.nivel == "critico")
    items = q.order_by(AlertaCapacitacion.nivel.desc(), AlertaCapacitacion.created_at.desc()).limit(100).all()
    return [_alerta_dict(a) for a in items]


def marcar_alerta_leida(empresa_id: int, alerta_id: int) -> dict:
    alerta = AlertaCapacitacion.query.filter_by(id=alerta_id, empresa_id=empresa_id).first()
    if not alerta:
        raise ValueError("Alerta no encontrada")
    alerta.leida = True
    db.session.commit()
    return _alerta_dict(alerta)


def _alerta_dict(a: AlertaCapacitacion) -> dict:
    return {
        "id": a.id,
        "tipo": a.tipo,
        "nivel": a.nivel,
        "titulo": a.titulo,
        "mensaje": a.mensaje,
        "fecha_referencia": a.fecha_referencia.isoformat() if a.fecha_referencia else None,
        "participante_id": a.participante_id,
        "curso_id": a.curso_id,
        "encuentro_id": a.encuentro_id,
        "leida": a.leida,
    }
