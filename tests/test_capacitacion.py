from datetime import date

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    Curso,
    Participante,
    PlanCapacitacion,
    Puesto,
    RegistroCapacitacion,
    RequisitoFormacion,
)
from gos.modulos.capacitacion.services import analitico_participante
from gos.modulos.objetivos.models.catalogos import Sector


def test_analitico_participante_pendientes_y_plan(app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        sector = Sector(empresa_id=emp.id, codigo="OP", nombre="Operaciones")
        db.session.add(sector)
        db.session.flush()

        puesto = Puesto(empresa_id=emp.id, codigo="TEC", nombre="Técnico")
        curso_a = Curso(empresa_id=emp.id, codigo="SEG-01", nombre="Seguridad básica")
        curso_b = Curso(empresa_id=emp.id, codigo="ISO-01", nombre="ISO 9001 intro")
        db.session.add_all([puesto, curso_a, curso_b])
        db.session.flush()

        participante = Participante(
            empresa_id=emp.id,
            sector_id=sector.id,
            puesto_id=puesto.id,
            legajo="1001",
            nombre="Juan Pérez",
        )
        db.session.add(participante)
        db.session.flush()

        db.session.add(
            RegistroCapacitacion(
                empresa_id=emp.id,
                participante_id=participante.id,
                curso_id=curso_a.id,
                fecha_realizacion=date(2025, 3, 1),
                nota=8.5,
                aprobado=True,
            )
        )
        db.session.add(
            RequisitoFormacion(
                empresa_id=emp.id,
                puesto_id=puesto.id,
                curso_id=curso_b.id,
                obligatorio=True,
            )
        )
        db.session.add(
            PlanCapacitacion(
                empresa_id=emp.id,
                participante_id=participante.id,
                curso_id=curso_b.id,
                fecha_planificada=date(2026, 7, 15),
                estado="programado",
            )
        )
        db.session.commit()

        data = analitico_participante(participante.id, empresa_id=emp.id)

        assert data["resumen"]["total_cursos_realizados"] == 1
        assert data["cursos_realizados"][0]["nota"] == 8.5
        assert data["resumen"]["total_pendientes"] == 1
        assert data["resumen"]["total_sin_planificar"] == 0
        assert len(data["planificacion"]) == 1
        assert data["planificacion"][0]["fecha_planificada"] == "2026-07-15"


def test_api_crear_curso_y_participante(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        sector = Sector(empresa_id=emp.id, codigo="RH", nombre="RRHH")
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    r = auth_client.post(
        "/gos/capacitacion/api/cursos",
        json={"codigo": "SEG-01", "nombre": "Seguridad", "horas": 8, "modalidad": "presencial"},
    )
    assert r.status_code == 201
    assert r.get_json()["curso"]["codigo"] == "SEG-01"

    r2 = auth_client.post(
        "/gos/capacitacion/api/puestos",
        json={"codigo": "OP", "nombre": "Operario"},
    )
    assert r2.status_code == 201
    puesto_id = r2.get_json()["puesto"]["id"]

    r3 = auth_client.post(
        "/gos/capacitacion/api/participantes",
        json={
            "nombre": "María López",
            "legajo": "2002",
            "sector_id": sector_id,
            "puesto_id": puesto_id,
        },
    )
    assert r3.status_code == 201
    assert r3.get_json()["participante"]["nombre"] == "María López"

    lista = auth_client.get("/gos/capacitacion/api/participantes")
    assert len(lista.get_json()["participantes"]) == 1


def test_api_crear_curso_duplicado(auth_client):
    auth_client.post(
        "/gos/capacitacion/api/cursos",
        json={"codigo": "DUP", "nombre": "Uno"},
    )
    r = auth_client.post(
        "/gos/capacitacion/api/cursos",
        json={"codigo": "DUP", "nombre": "Dos"},
    )
    assert r.status_code == 400
    assert "código" in r.get_json()["error"].lower()


def test_api_alumno_no_puede_crear(alumno_client):
    r = alumno_client.post(
        "/gos/capacitacion/api/cursos",
        json={"codigo": "X", "nombre": "Test"},
    )
    assert r.status_code == 403


def test_api_crear_y_editar_sector_y_puesto(auth_client):
    r = auth_client.post(
        "/gos/capacitacion/api/sectores",
        json={"codigo": "OP", "nombre": "Operaciones"},
    )
    assert r.status_code == 201
    sector_id = r.get_json()["sector"]["id"]

    r2 = auth_client.put(
        f"/gos/capacitacion/api/sectores/{sector_id}",
        json={"codigo": "OP", "nombre": "Operaciones y Logística"},
    )
    assert r2.status_code == 200
    assert r2.get_json()["sector"]["nombre"] == "Operaciones y Logística"

    r3 = auth_client.post(
        "/gos/capacitacion/api/puestos",
        json={"codigo": "TEC", "nombre": "Técnico"},
    )
    assert r3.status_code == 201
    puesto_id = r3.get_json()["puesto"]["id"]

    r4 = auth_client.put(
        f"/gos/capacitacion/api/puestos/{puesto_id}",
        json={"codigo": "TEC", "nombre": "Técnico senior"},
    )
    assert r4.status_code == 200
    assert r4.get_json()["puesto"]["nombre"] == "Técnico senior"


def test_api_editar_participante_sector_puesto(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        s1 = Sector(empresa_id=emp.id, codigo="A", nombre="Sector A")
        s2 = Sector(empresa_id=emp.id, codigo="B", nombre="Sector B")
        db.session.add_all([s1, s2])
        db.session.flush()
        puesto = Puesto(empresa_id=emp.id, codigo="P1", nombre="Puesto 1")
        db.session.add(puesto)
        db.session.flush()
        participante = Participante(empresa_id=emp.id, sector_id=s1.id, puesto_id=puesto.id, nombre="Ana")
        db.session.add(participante)
        db.session.commit()
        pid = participante.id
        s2_id = s2.id
        puesto_id = puesto.id

    r = auth_client.put(
        f"/gos/capacitacion/api/participantes/{pid}",
        json={"nombre": "Ana", "sector_id": s2_id, "puesto_id": puesto_id},
    )
    assert r.status_code == 200
    assert r.get_json()["participante"]["sector_id"] == s2_id
