"""Notificaciones por email integradas con cap_alertas."""

from __future__ import annotations

from datetime import datetime, timezone

from gos.extensions import db
from gos.models import Empresa, Usuario
from gos.modulos.capacitacion.models import AlertaCapacitacion, Participante
from gos.modulos.capacitacion.models.config import CapacitacionConfig
from gos.modulos.capacitacion.services.config_service import obtener_config
from gos.services import mail_service

_TIPO_FILTRO = {
    "vencimiento": "notif_vencimiento",
    "pendiente_obligatorio": "notif_obligatorio",
    "curso_proximo": "notif_curso_proximo",
}


def _destinatarios_para_alerta(empresa_id: int, alerta: AlertaCapacitacion, cfg: dict) -> set[str]:
    emails: set[str] = set(cfg.get("emails_destinatarios") or [])

    sector_id = None
    if alerta.participante_id:
        p = Participante.query.get(alerta.participante_id)
        if p:
            sector_id = p.sector_id
            if p.email:
                emails.add(p.email.strip().lower())

    if sector_id is not None:
        por_sector = cfg.get("emails_por_sector") or {}
        emails.update(por_sector.get(str(sector_id), []))

    por_rol = cfg.get("emails_por_rol") or {}
    if por_rol:
        usuarios = Usuario.query.filter_by(empresa_id=empresa_id, activo=True).all()
        for u in usuarios:
            if u.rol in por_rol and u.email:
                emails.add(u.email.strip().lower())

    if not emails:
        admins = Usuario.query.filter_by(empresa_id=empresa_id, activo=True).filter(
            Usuario.rol.in_(("administrador", "angel"))
        ).all()
        for u in admins:
            if u.email:
                emails.add(u.email.strip().lower())

    return emails


def _alertas_enviables(empresa_id: int, cfg: dict) -> list[AlertaCapacitacion]:
    alertas = AlertaCapacitacion.query.filter_by(empresa_id=empresa_id, resuelta=False).all()
    resultado = []
    for a in alertas:
        flag = _TIPO_FILTRO.get(a.tipo)
        if flag and not cfg.get(flag, True):
            continue
        resultado.append(a)
    return resultado


def _armar_cuerpo(empresa_nombre: str, alertas: list[AlertaCapacitacion]) -> tuple[str, str]:
    por_tipo: dict[str, list[AlertaCapacitacion]] = {}
    for a in alertas:
        por_tipo.setdefault(a.tipo, []).append(a)

    lineas = [f"Resumen de alertas — {empresa_nombre}", ""]
    html_parts = [f"<h2>Alertas de capacitación — {empresa_nombre}</h2>"]

    etiquetas = {
        "vencimiento": "Vencimientos próximos / vencidos",
        "pendiente_obligatorio": "Capacitaciones obligatorias pendientes",
        "curso_proximo": "Cursos programados",
    }
    for tipo, items in por_tipo.items():
        titulo = etiquetas.get(tipo, tipo)
        lineas.append(f"## {titulo} ({len(items)})")
        html_parts.append(f"<h3>{titulo} ({len(items)})</h3><ul>")
        for a in items[:50]:
            lineas.append(f"  • [{a.nivel}] {a.titulo}: {a.mensaje or ''}")
            html_parts.append(f"<li><strong>[{a.nivel}]</strong> {a.titulo}: {a.mensaje or ''}</li>")
        if len(items) > 50:
            lineas.append(f"  … y {len(items) - 50} más")
            html_parts.append(f"<li>… y {len(items) - 50} más</li>")
        lineas.append("")
        html_parts.append("</ul>")

    lineas.append("— GOS Capacitaciones")
    html_parts.append("<p><em>GOS Capacitaciones</em></p>")
    return "\n".join(lineas), "".join(html_parts)


def enviar_notificaciones_alertas(empresa_id: int) -> dict:
    """Envía email con alertas activas según configuración."""
    cfg = obtener_config(empresa_id)
    if not cfg.get("notif_email_activo"):
        return {"enviado": False, "motivo": "notificaciones_desactivadas", "destinatarios": []}

    alertas = _alertas_enviables(empresa_id, cfg)
    if not alertas:
        return {"enviado": False, "motivo": "sin_alertas", "destinatarios": []}

    destinatarios: set[str] = set()
    for a in alertas:
        destinatarios.update(_destinatarios_para_alerta(empresa_id, a, cfg))

    if not destinatarios:
        return {"enviado": False, "motivo": "sin_destinatarios", "destinatarios": []}

    emp = Empresa.query.get(empresa_id)
    nombre = emp.nombre if emp else "Empresa"
    texto, html = _armar_cuerpo(nombre, alertas)
    subject = f"[GOS] {len(alertas)} alerta(s) de capacitación — {nombre}"

    ok = mail_service.send_email(
        to=sorted(destinatarios),
        subject=subject,
        body_text=texto,
        body_html=html,
    )
    if ok:
        cap_cfg = CapacitacionConfig.query.filter_by(empresa_id=empresa_id).first()
        if cap_cfg:
            cap_cfg.ultimo_envio_notif = datetime.now(timezone.utc)
            db.session.commit()

    return {
        "enviado": ok,
        "motivo": None if ok else "smtp_no_configurado",
        "destinatarios": sorted(destinatarios),
        "alertas_incluidas": len(alertas),
    }
