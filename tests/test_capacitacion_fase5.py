"""Tests Fase 5 — búsqueda, dashboard tipo, sync vacaciones."""
from datetime import date

from gos.extensions import db
from gos.modulos.capacitacion.models import Curso, Participante, ProgramaCapacitacion
from gos.modulos.capacitacion.services.busqueda_service import busqueda_global
from gos.modulos.capacitacion.services.dashboard_service import resumen_dashboard
from gos.modulos.capacitacion.services.sync_service import sincronizar_legajos_vacaciones
from gos.modulos.objetivos.models.catalogos import Sector


def test_busqueda_global(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        db.session.add(Participante(empresa_id=emp.id, nombre="María López", legajo="777"))
        db.session.add(Curso(empresa_id=emp.id, codigo="BUS-1", nombre="Curso Búsqueda"))
        db.session.add(
            ProgramaCapacitacion(
                empresa_id=emp.id,
                codigo="PRG-1",
                nombre="Programa Alpha",
                estado="activo",
            )
        )
        db.session.commit()

    r = auth_client.get("/gos/capacitacion/api/busqueda?q=777")
    assert r.status_code == 200
    tipos = {x["tipo"] for x in r.get_json()["resultados"]}
    assert "participante" in tipos

    r2 = auth_client.get("/gos/capacitacion/api/busqueda?q=bus")
    assert any(x["tipo"] == "curso" for x in r2.get_json()["resultados"])


def test_busqueda_minimo_caracteres(app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        assert busqueda_global(emp.id, "a")["resultados"] == []


def test_dashboard_cumplimiento_por_tipo(app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        db.session.add(
            Curso(empresa_id=emp.id, codigo="HSE-1", nombre="Seguridad", tipo_capacitacion="hse")
        )
        db.session.commit()
        data = resumen_dashboard(emp.id)
    assert "cumplimiento_por_tipo" in data


def test_sync_vacaciones_sector(app, monkeypatch):
    """Sync enriquecido: sector y fecha_ingreso desde Vacaciones."""
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        sector = Sector(empresa_id=emp.id, codigo="OP", nombre="Operaciones", activo=True)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    class FakeVacacion:
        legajo = 12345
        empleado = "Pedro Sync"
        sector = "Operaciones"
        fecha_ingreso = date(2020, 3, 15)

    class FakeQuery:
        def all(self):
            return [FakeVacacion()]

    class FakeSession:
        def query(self, model):
            return FakeQuery()

        def close(self):
            pass

    monkeypatch.setattr(
        "gos.modulos.vacaciones.database.get_session",
        lambda: FakeSession(),
    )

    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        result = sincronizar_legajos_vacaciones(emp.id)
        assert result["creados"] == 1
        p = Participante.query.filter_by(empresa_id=emp.id, legajo="12345").first()
        assert p is not None
        assert p.sector_id == sector_id
        assert p.fecha_ingreso == date(2020, 3, 15)
