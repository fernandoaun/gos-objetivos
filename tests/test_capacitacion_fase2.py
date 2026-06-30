from gos.extensions import db
from gos.modulos.capacitacion.models import Curso, Participante, Puesto


def test_api_requisitos_por_puesto(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        puesto = Puesto(empresa_id=emp.id, codigo="OP", nombre="Operario")
        curso = Curso(empresa_id=emp.id, codigo="SEG-01", nombre="Seguridad")
        db.session.add_all([puesto, curso])
        db.session.commit()
        puesto_id, curso_id = puesto.id, curso.id

    r = auth_client.post(
        "/gos/capacitacion/api/requisitos",
        json={"puesto_id": puesto_id, "curso_id": curso_id, "obligatorio": True},
    )
    assert r.status_code == 201
    req_id = r.get_json()["requisito"]["id"]

    lista = auth_client.get(f"/gos/capacitacion/api/requisitos?puesto_id={puesto_id}")
    assert len(lista.get_json()["requisitos"]) == 1

    r2 = auth_client.delete(f"/gos/capacitacion/api/requisitos/{req_id}")
    assert r2.status_code == 200


def test_api_actualizar_y_baja_curso(auth_client):
    r = auth_client.post(
        "/gos/capacitacion/api/cursos",
        json={"codigo": "CUR-1", "nombre": "Curso uno", "horas": 4},
    )
    curso_id = r.get_json()["curso"]["id"]

    r2 = auth_client.put(
        f"/gos/capacitacion/api/cursos/{curso_id}",
        json={
            "codigo": "CUR-1",
            "nombre": "Curso actualizado",
            "horas": 8,
            "categoria": "hse",
            "tipo": "obligatoria",
            "origen": "interna",
            "modalidad": "presencial",
        },
    )
    assert r2.status_code == 200
    assert r2.get_json()["curso"]["nombre"] == "Curso actualizado"

    r3 = auth_client.delete(f"/gos/capacitacion/api/cursos/{curso_id}")
    assert r3.status_code == 200

    lista = auth_client.get("/gos/capacitacion/api/cursos")
    assert all(c["id"] != curso_id for c in lista.get_json()["cursos"])


def test_importar_participantes_excel(auth_client, app):
    from io import BytesIO

    import openpyxl

    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        puesto = Puesto(empresa_id=emp.id, codigo="TEC", nombre="Técnico")
        db.session.add(puesto)
        db.session.commit()

    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    ws2.append(["nombre", "apellido", "legajo", "puesto_codigo"])
    ws2.append(["Ana", "García", "3001", "TEC"])
    buf2 = BytesIO()
    wb2.save(buf2)
    buf2.seek(0)

    r = auth_client.post(
        "/gos/capacitacion/api/participantes/importar",
        data={"archivo": (buf2, "personal.xlsx")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["creados"] == 1

    lista = auth_client.get("/gos/capacitacion/api/participantes?activo=all")
    nombres = [p["nombre"] for p in lista.get_json()["participantes"]]
    assert any("Ana" in n for n in nombres)


def test_registrar_asistencias(auth_client, app):
    from datetime import date

    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        curso = Curso(empresa_id=emp.id, codigo="IND-01", nombre="Inducción", vigencia_meses=12)
        p = Participante(empresa_id=emp.id, nombre="Pedro", legajo="4001")
        db.session.add_all([curso, p])
        db.session.flush()
        from gos.modulos.capacitacion.models import EncuentroCapacitacion

        enc = EncuentroCapacitacion(
            empresa_id=emp.id,
            curso_id=curso.id,
            titulo="Inducción día 1",
            fecha=date(2026, 3, 10),
            estado="programado",
        )
        db.session.add(enc)
        db.session.commit()
        enc_id, pid = enc.id, p.id

    r = auth_client.post(
        f"/gos/capacitacion/api/encuentros/{enc_id}/asistencias",
        json={
            "asistencias": [
                {"participante_id": pid, "asistencia": "presente", "nota": 9, "aprobado": True}
            ]
        },
    )
    assert r.status_code == 200
    assert r.get_json()["guardados"] == 1

    det = auth_client.get(f"/gos/capacitacion/api/encuentros/{enc_id}")
    assert det.get_json()["estado"] == "realizado"
