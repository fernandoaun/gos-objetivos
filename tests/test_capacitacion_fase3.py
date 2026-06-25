"""Tests Fase 3 — Capacitaciones: PDF, ISO, certificados, config."""
from datetime import date
from io import BytesIO

from gos.extensions import db
from gos.modulos.capacitacion.models import Curso, Participante, RegistroCapacitacion
from gos.modulos.capacitacion.services.pdf_export_service import (
    generar_pdf_general,
    generar_pdf_iso,
    generar_pdf_participante,
)
from gos.modulos.capacitacion.services.reporte_service import reporte_iso


def test_api_configuracion_umbrales(auth_client):
    r = auth_client.get("/gos/capacitacion/api/configuracion")
    assert r.status_code == 200
    assert r.get_json()["config"]["dias_proximo_vencer"] == 30

    r2 = auth_client.put(
        "/gos/capacitacion/api/configuracion",
        json={"dias_proximo_vencer": 45, "dias_encuentro_proximo": 14},
    )
    assert r2.status_code == 200
    assert r2.get_json()["config"]["dias_proximo_vencer"] == 45
    assert r2.get_json()["config"]["dias_encuentro_proximo"] == 14


def test_api_configuracion_alumno_no_edita(alumno_client):
    r = alumno_client.put(
        "/gos/capacitacion/api/configuracion",
        json={"dias_proximo_vencer": 10},
    )
    assert r.status_code == 403


def test_subir_certificado_pdf(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        curso = Curso(empresa_id=emp.id, codigo="PDF-01", nombre="Curso PDF")
        p = Participante(empresa_id=emp.id, nombre="Test", legajo="9001")
        db.session.add_all([curso, p])
        db.session.flush()
        reg = RegistroCapacitacion(
            empresa_id=emp.id,
            participante_id=p.id,
            curso_id=curso.id,
            fecha_realizacion=date(2026, 1, 15),
            aprobado=True,
        )
        db.session.add(reg)
        db.session.commit()
        reg_id = reg.id

    pdf_bytes = b"%PDF-1.4 test content"
    r = auth_client.post(
        f"/gos/capacitacion/api/registros/{reg_id}/certificado",
        data={"archivo": (BytesIO(pdf_bytes), "cert.pdf")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    assert r.get_json()["registro"]["tiene_certificado"] is True

    r2 = auth_client.get(f"/gos/capacitacion/api/registros/{reg_id}/certificado")
    assert r2.status_code == 200
    assert r2.data.startswith(b"%PDF")


def test_reporte_iso_9001(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        curso = Curso(
            empresa_id=emp.id,
            codigo="ISO-9001-INT",
            nombre="Intro ISO 9001",
            tipo_capacitacion="sgi",
        )
        db.session.add(curso)
        db.session.commit()

    r = auth_client.get("/gos/capacitacion/api/reportes/iso/9001")
    assert r.status_code == 200
    data = r.get_json()
    assert data["norma"] == "9001"
    assert "resumen" in data


def test_reporte_iso_pdf_bytes(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        data = reporte_iso(emp.id, "9001")
        pdf = generar_pdf_iso(emp.nombre, emp.id, "9001")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 300


def test_pdf_participante_y_general(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        p = Participante(empresa_id=emp.id, nombre="Ana", legajo="100")
        db.session.add(p)
        db.session.commit()
        pid = p.id

    r = auth_client.get(f"/gos/capacitacion/api/participantes/{pid}/reporte.pdf")
    assert r.status_code == 200
    assert r.data.startswith(b"%PDF")

    r2 = auth_client.get("/gos/capacitacion/api/reportes/general.pdf")
    assert r2.status_code == 200
    assert r2.data.startswith(b"%PDF")

    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        pdf = generar_pdf_participante(emp.nombre, pid, emp.id)
        pdf_g = generar_pdf_general(emp.nombre, emp.id)
    assert pdf.startswith(b"%PDF")
    assert pdf_g.startswith(b"%PDF")
