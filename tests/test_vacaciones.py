import pytest

from gos.modulos.vacaciones import storage
from gos.modulos.vacaciones.models import Registro, Vacacion


@pytest.fixture(autouse=True)
def vacaciones_db(app):
    with app.app_context():
        storage.reset_for_tests()
        yield
        storage.reset_for_tests()


def test_vacaciones_health_requires_auth(client):
    r = client.get("/gos/vacaciones/api/health")
    assert r.status_code == 302
    assert "/auth/login" in r.location


def test_vacaciones_health_ok(auth_client):
    r = auth_client.get("/gos/vacaciones/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


def test_vacaciones_shell(auth_client):
    r = auth_client.get("/gos/vacaciones/")
    assert r.status_code == 200
    assert b"vac-frame" in r.data


def test_vacaciones_app(auth_client):
    r = auth_client.get("/gos/vacaciones/app/")
    assert r.status_code == 200
    assert b"Vacaciones Adeudadas" in r.data


def test_vacaciones_deuda_empty(auth_client):
    r = auth_client.get("/gos/vacaciones/api/vacaciones/deuda")
    assert r.status_code == 200
    assert r.get_json() == []


def test_vacaciones_dashboard_lists(auth_client, app):
    with app.app_context():
        from datetime import date

        from gos.extensions import db

        db.session.add(
            Registro(fecha=date(2025, 6, 1), empleado="Ana Test", sector="IT", vacaciones=0)
        )
        db.session.add(
            Vacacion(
                legajo=1,
                empleado="Ana Test",
                sector="IT",
                anio=2025,
                dias_disponibles=14,
                dias_tomados=5,
                dias_pendientes=9,
            )
        )
        db.session.commit()

    r = auth_client.get("/gos/vacaciones/api/dashboard/años")
    assert r.status_code == 200
    assert 2025 in r.get_json()

    r = auth_client.get("/gos/vacaciones/api/dashboard/sectores")
    assert r.status_code == 200
    assert "IT" in r.get_json()

    r = auth_client.get("/gos/vacaciones/api/dashboard/empleados")
    assert r.status_code == 200
    assert "Ana Test" in r.get_json()


def test_vacaciones_import_excel(auth_client):
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TOTAL"
    ws.append([
        "fecha", "empleado", "sector", "servicio", "centro", "situacion",
        "total_horas", "hs_viaje", "hs50", "hs_noc", "hs_noc50", "hs100",
        "viandas", "v_desayuno", "d_normales", "ausente", "fr_trabajados",
        "feriados", "enfermedad", "traslado", "vacaciones", "licencia",
        "suspension", "accidente", "francos_comp",
    ])
    ws.append([
        "2025-06-01", "Pedro Test", "RRHH", "", "", "", 8, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0,
    ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    r = auth_client.post(
        "/gos/vacaciones/api/importar/excel",
        data={"file": (buf, "test.xlsx")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["detalle"]["registros"] == 1
