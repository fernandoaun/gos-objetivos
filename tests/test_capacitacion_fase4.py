"""Tests Fase 4 — notificaciones email y configuración extendida."""
from datetime import date, timedelta

from gos.extensions import db
from gos.modulos.capacitacion.models import AlertaCapacitacion, Curso, Participante, RegistroCapacitacion
from gos.modulos.capacitacion.services.alerta_service import generar_alertas
from gos.modulos.capacitacion.services.config_service import guardar_config
from gos.modulos.capacitacion.services.notificacion_service import enviar_notificaciones_alertas
from gos.services import mail_service


def test_config_notificaciones_extendida(auth_client):
    r = auth_client.put(
        "/gos/capacitacion/api/configuracion",
        json={
            "dias_proximo_vencer": 20,
            "pct_cumplimiento_minimo": 75,
            "notif_email_activo": True,
            "notif_vencimiento": True,
            "notif_obligatorio": False,
            "emails_destinatarios": ["rrhh@test.com"],
            "emails_por_rol": {"administrador": ["admin@test.com"]},
        },
    )
    assert r.status_code == 200
    cfg = r.get_json()["config"]
    assert cfg["notif_email_activo"] is True
    assert cfg["pct_cumplimiento_minimo"] == 75
    assert "rrhh@test.com" in cfg["emails_destinatarios"]


def test_generar_alertas_y_notificar(auth_client, app):
    mail_service.clear_sent_log()
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        guardar_config(
            emp.id,
            {
                "notif_email_activo": True,
                "emails_destinatarios": ["alertas@test.com"],
            },
        )
        curso = Curso(empresa_id=emp.id, codigo="AL-01", nombre="Alerta Test")
        p = Participante(empresa_id=emp.id, nombre="Juan", legajo="500")
        db.session.add_all([curso, p])
        db.session.flush()
        reg = RegistroCapacitacion(
            empresa_id=emp.id,
            participante_id=p.id,
            curso_id=curso.id,
            fecha_realizacion=date.today() - timedelta(days=400),
            vigente_hasta=date.today() - timedelta(days=1),
            aprobado=True,
        )
        db.session.add(reg)
        db.session.commit()

    r = auth_client.post("/gos/capacitacion/api/alertas/generar", json={})
    assert r.status_code == 200
    data = r.get_json()
    assert data["generadas"] >= 1
    assert data["notificacion"]["enviado"] is True
    assert "alertas@test.com" in data["notificacion"]["destinatarios"]
    assert len(mail_service.get_sent_log()) == 1


def test_notificar_manual_sin_alertas(auth_client, app):
    mail_service.clear_sent_log()
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        guardar_config(emp.id, {"notif_email_activo": True, "emails_destinatarios": ["x@test.com"]})
        AlertaCapacitacion.query.filter_by(empresa_id=emp.id).delete()
        db.session.commit()

    r = auth_client.post("/gos/capacitacion/api/alertas/notificar", json={})
    assert r.status_code == 200
    assert r.get_json()["notificacion"]["motivo"] == "sin_alertas"


def test_configuracion_page(auth_client):
    r = auth_client.get("/gos/capacitacion/configuracion")
    assert r.status_code == 200


def test_enviar_notificaciones_desactivadas(app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        guardar_config(emp.id, {"notif_email_activo": False})
        result = enviar_notificaciones_alertas(emp.id)
    assert result["enviado"] is False
    assert result["motivo"] == "notificaciones_desactivadas"
