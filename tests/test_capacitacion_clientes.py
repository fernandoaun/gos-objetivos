from io import BytesIO

from gos.extensions import db
from gos.models import Empresa
from gos.modulos.capacitacion.models import ClienteCapacitacion, Participante, ParticipanteCliente
from gos.modulos.capacitacion.services.catalogo_service import actualizar_participante, crear_participante
from gos.modulos.capacitacion.services.cliente_service import actualizar_cliente, crear_cliente
from gos.modulos.capacitacion.services.dashboard_service import informe_cliente


def test_persona_puede_afectarse_a_varios_clientes(app):
    with app.app_context():
        emp = Empresa.query.first()
        a = crear_cliente(emp.id, {"nombre": "Cliente Norte", "codigo": "CN"})
        b = crear_cliente(emp.id, {"nombre": "Cliente Sur", "codigo": "CS"})
        persona = crear_participante(
            emp.id,
            {
                "nombre": "Ana Informe",
                "legajo": "CLI-1",
                "cliente_ids": [a["id"], b["id"]],
            },
        )
        assert set(persona["cliente_ids"]) == {a["id"], b["id"]}

        otra = crear_participante(emp.id, {"nombre": "Bruno Solo", "legajo": "CLI-2"})
        actualizar_participante(emp.id, otra["id"], {
            "nombre": "Bruno Solo",
            "legajo": "CLI-2",
            "cliente_ids": [a["id"]],
        })

        norte = informe_cliente(emp.id, a["id"])
        ids = {p["id"] for p in norte["personas_detalle"]}
        assert persona["id"] in ids
        assert otra["id"] in ids
        assert norte["kpis"]["personas_activas"] == 2
        assert norte["cliente"]["nombre"] == "Cliente Norte"

        sur = informe_cliente(emp.id, b["id"])
        sur_ids = {p["id"] for p in sur["personas_detalle"]}
        assert persona["id"] in sur_ids
        assert otra["id"] not in sur_ids
        assert sur["kpis"]["personas_activas"] == 1


def test_api_clientes_e_informe(auth_client, app):
    with app.app_context():
        emp = Empresa.query.first()
        crear_cliente(emp.id, {"nombre": "Acme SA", "codigo": "ACME"})
        crear_participante(emp.id, {"nombre": "Carla", "legajo": "C-9"})

    created = auth_client.post(
        "/gos/capacitacion/api/clientes",
        json={"nombre": "Beta SRL"},
    )
    assert created.status_code == 201
    cliente_id = created.get_json()["cliente"]["id"]

    listed = auth_client.get("/gos/capacitacion/api/clientes")
    assert listed.status_code == 200
    nombres = {c["nombre"] for c in listed.get_json()["clientes"]}
    assert "Acme SA" in nombres
    assert "Beta SRL" in nombres

    with app.app_context():
        emp = Empresa.query.first()
        persona = Participante.query.filter_by(empresa_id=emp.id, legajo="C-9").first()
        db.session.add(ParticipanteCliente(participante_id=persona.id, cliente_id=cliente_id))
        db.session.commit()

    informe = auth_client.get(f"/gos/capacitacion/api/clientes/{cliente_id}/informe")
    assert informe.status_code == 200
    body = informe.get_json()
    assert body["cliente"]["nombre"] == "Beta SRL"
    assert body["kpis"]["personas_activas"] == 1
    assert body["personas_detalle"][0]["nombre"] == "Carla"


def test_logo_cliente_se_conserva_al_editar_y_con_ruta_invalida(auth_client, app):
    png = b"\x89PNG\r\n\x1a\n" + b"logo-pampa"
    with app.app_context():
        emp = Empresa.query.first()
        cliente = crear_cliente(emp.id, {"nombre": "PAMPA ENERGIA", "codigo": "PAM"})
        cid = cliente["id"]

    uploaded = auth_client.post(
        f"/gos/capacitacion/api/clientes/{cid}/logo",
        data={"archivo": (BytesIO(png), "pampa.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200
    assert uploaded.get_json()["cliente"]["tiene_logo"] is True

    with app.app_context():
        emp = Empresa.query.first()
        actualizar_cliente(emp.id, cid, {"nombre": "PAMPA ENERGIA", "codigo": "PAM"})
        row = db.session.get(ClienteCapacitacion, cid)
        assert row.logo_bytes
        row.logo_path = r"C:\maquina-vieja\storage\cli_1.png"
        db.session.commit()

    listed = auth_client.get("/gos/capacitacion/api/clientes")
    assert listed.status_code == 200
    item = next(c for c in listed.get_json()["clientes"] if c["id"] == cid)
    assert item["tiene_logo"] is True

    logo = auth_client.get(f"/gos/capacitacion/api/clientes/{cid}/logo")
    assert logo.status_code == 200
    assert logo.data.startswith(b"\x89PNG")
