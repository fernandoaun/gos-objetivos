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


def test_dashboard_recursos_habilitado_por_defecto(app):
    """Sin curso programado = habilitado. Requisito de catálogo no inhabilita.
    Cae si desaprobó o si el encuentro ya se dictó y el mes programado venció."""
    from gos.modulos.capacitacion.models import (
        AsistenciaEncuentro,
        EncuentroCapacitacion,
        Puesto,
        RequisitoFormacion,
    )

    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        puesto = Puesto(empresa_id=emp.id, codigo="TEC-H", nombre="Técnico Hab")
        curso = Curso(empresa_id=emp.id, codigo="HAB-1", nombre="Curso habilitación")
        db.session.add_all([puesto, curso])
        db.session.flush()

        sin_cursos = Participante(empresa_id=emp.id, nombre="Sin Cursos", legajo="H1")
        con_req = Participante(
            empresa_id=emp.id, nombre="Con Requisito", legajo="H2", puesto_id=puesto.id
        )
        vencido = Participante(empresa_id=emp.id, nombre="Vencido", legajo="H3")
        desaprobo = Participante(empresa_id=emp.id, nombre="Desaprobó", legajo="H4")
        en_plazo = Participante(empresa_id=emp.id, nombre="En Plazo", legajo="H5")
        db.session.add_all([sin_cursos, con_req, vencido, desaprobo, en_plazo])
        db.session.flush()

        db.session.add(
            RequisitoFormacion(
                empresa_id=emp.id,
                puesto_id=puesto.id,
                curso_id=curso.id,
                obligatorio=True,
            )
        )

        enc_venc = EncuentroCapacitacion(
            empresa_id=emp.id,
            curso_id=curso.id,
            titulo="Sesión vencida",
            fecha=date(2026, 6, 1),
            estado="cerrado",
        )
        enc_fail = EncuentroCapacitacion(
            empresa_id=emp.id,
            curso_id=curso.id,
            titulo="Sesión desaprobada",
            fecha=date(2026, 8, 1),
            estado="planificado",
        )
        enc_ok = EncuentroCapacitacion(
            empresa_id=emp.id,
            curso_id=curso.id,
            titulo="Sesión en plazo",
            fecha=date(2026, 8, 1),
            estado="planificado",
        )
        db.session.add_all([enc_venc, enc_fail, enc_ok])
        db.session.flush()
        db.session.add_all(
            [
                AsistenciaEncuentro(
                    encuentro_id=enc_venc.id,
                    participante_id=vencido.id,
                    asistencia="inscripto",
                ),
                AsistenciaEncuentro(
                    encuentro_id=enc_fail.id,
                    participante_id=desaprobo.id,
                    asistencia="presente",
                    aprobado=False,
                ),
                AsistenciaEncuentro(
                    encuentro_id=enc_ok.id,
                    participante_id=en_plazo.id,
                    asistencia="inscripto",
                ),
            ]
        )
        db.session.commit()

        data = resumen_dashboard(emp.id)
        personal = next(r for r in data["recursos"] if r["clave"] == "personal")
        assert personal["verde"] == 3
        assert personal["rojo"] == 2
        assert personal["gris"] == 0
        assert data["habilitados_pct"] == 60
        assert data["inhabilitados_pct"] == 40


def test_asignacion_inhabilita_no_penaliza_roster_ni_acreditacion_default():
    """Inscripto masivo / Acreditacion.aprobo=False sin evaluar no inhabilitan."""
    from types import SimpleNamespace

    from gos.modulos.capacitacion.services.dashboard_service import (
        _asignacion_inhabilita,
        persona_habilitada_por_programados,
    )

    hoy = date(2026, 8, 14)

    def enc(**kw):
        base = dict(
            estado="planificado",
            curso_id=1,
            fecha=date(2026, 8, 1),
            es_buenas_practicas=False,
            fecha_realizacion=None,
        )
        base.update(kw)
        return SimpleNamespace(**base)

    def asist(**kw):
        base = dict(asistencia="inscripto", aprobado=None)
        base.update(kw)
        return SimpleNamespace(**base)

    assert persona_habilitada_por_programados([], hoy, set()) is True
    assert (
        _asignacion_inhabilita(
            asist(), enc(fecha=date(2026, 6, 1), estado="planificado"), None, hoy, set()
        )
        is False
    )
    assert (
        _asignacion_inhabilita(
            asist(), enc(fecha=date(2026, 6, 1), estado="cerrado"), None, hoy, set()
        )
        is True
    )
    assert (
        _asignacion_inhabilita(asist(asistencia="presente", aprobado=False), enc(), None, hoy, set())
        is True
    )
    assert (
        _asignacion_inhabilita(asist(aprobado=0), enc(fecha=date(2026, 6, 1), estado="cerrado"), None, hoy, set())
        is True
    )
    assert (
        _asignacion_inhabilita(
            asist(), enc(fecha=date(2026, 6, 1), estado="cerrado", curso_id=9), None, hoy, {9}
        )
        is False
    )
    acr_default = SimpleNamespace(
        aprobo=False, nota=None, fecha_aprobacion=None, fecha_vencimiento=None
    )
    assert _asignacion_inhabilita(asist(), enc(), acr_default, hoy, set()) is False
    acr_fail = SimpleNamespace(aprobo=False, nota=4, fecha_aprobacion=None, fecha_vencimiento=None)
    assert _asignacion_inhabilita(asist(asistencia="presente"), enc(), acr_fail, hoy, set()) is True
    bpc = enc(fecha=date(2026, 6, 1), estado="cerrado", es_buenas_practicas=True)
    assert _asignacion_inhabilita(asist(), bpc, None, hoy, set()) is False


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
