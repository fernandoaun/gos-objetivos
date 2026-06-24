import pytest

from gos.modulos.vacaciones.database import DATA_DIR, get_session, init_db, reset_for_tests
from gos.modulos.vacaciones.models import Registro, Vacacion


@pytest.fixture(autouse=True)
def vacaciones_db(app):
    reset_for_tests()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    yield
    reset_for_tests()


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


def test_vacaciones_dashboard_lists(auth_client):
    db = get_session()
    try:
        from datetime import date

        db.add(
            Registro(
                fecha=date(2024, 6, 1),
                empleado="Juan Pérez",
                sector="Planta",
                vacaciones=1,
            )
        )
        db.add(
            Vacacion(
                legajo=1,
                empleado="Juan Pérez",
                sector="Planta",
                anio=2024,
                dias_disponibles=14,
                dias_tomados=10,
                dias_pendientes=4,
            )
        )
        db.commit()
    finally:
        db.close()

    r = auth_client.get("/gos/vacaciones/api/dashboard/empleados")
    assert r.status_code == 200
    assert "Juan Pérez" in r.get_json()

    r = auth_client.get("/gos/vacaciones/api/vacaciones/deuda?desde=2024-01-01&hasta=2024-12-31")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["empleado"] == "Juan Pérez"
    assert data[0]["tomados_real"] == 1
