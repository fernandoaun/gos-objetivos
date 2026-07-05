"""Tests Fase 6 — cronograma cierre, acreditación múltiple, matriz analítica."""
from datetime import date, datetime

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    Acreditacion,
    Curso,
    Participante,
    PlanCurso,
    ProgramaCapacitacion,
    ProgramaPlan,
    ProgramaPuesto,
    Puesto,
)
from gos.modulos.capacitacion.models.programa import EncuentroCapacitacion
from gos.modulos.capacitacion.models.registro import AsistenciaEncuentro
from gos.modulos.capacitacion.services.acreditacion_service import calcular_aprobacion
from gos.modulos.capacitacion.services.matriz_analitica_service import (
    _estado_acreditacion,
    matriz_analitica,
    matriz_filtros_metadata,
)


def test_calcular_aprobacion_reglas():
    curso_sin_eval = Curso(requiere_evaluacion=False)
    curso_con_eval = Curso(requiere_evaluacion=True, puntaje_minimo=7)
    assert calcular_aprobacion(False, None, curso_sin_eval) is False
    assert calcular_aprobacion(True, None, curso_sin_eval) is True
    assert calcular_aprobacion(True, 8, curso_con_eval) is True
    assert calcular_aprobacion(True, 6, curso_con_eval) is False


def test_estado_vencido_es_pendiente():
    acr = Acreditacion(aprobo=True, vigente=False, fecha_vencimiento=date(2020, 1, 1))
    assert _estado_acreditacion(acr, date.today()) == "pendiente"


def test_cierre_acredita_multiples_programas(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        puesto = Puesto(empresa_id=emp.id, codigo="T6", nombre="Técnico VI")
        curso = Curso(
            empresa_id=emp.id,
            codigo="MULTI-1",
            nombre="Curso compartido",
            horas=4,
            requiere_evaluacion=False,
        )
        persona = Participante(empresa_id=emp.id, nombre="Test Multi", legajo="6001", puesto_id=None)
        db.session.add_all([puesto, curso, persona])
        db.session.flush()
        persona.puesto_id = puesto.id

        prog_a = ProgramaCapacitacion(empresa_id=emp.id, codigo="PA", nombre="Programa A", tipo="interno")
        prog_b = ProgramaCapacitacion(empresa_id=emp.id, codigo="PB", nombre="Programa B", tipo="interno")
        db.session.add_all([prog_a, prog_b])
        db.session.flush()

        plan_a = ProgramaPlan(programa_id=prog_a.id, nombre="Plan A", orden=1)
        plan_b = ProgramaPlan(programa_id=prog_b.id, nombre="Plan B", orden=1)
        db.session.add_all([plan_a, plan_b])
        db.session.flush()

        db.session.add_all([
            ProgramaPuesto(programa_id=prog_a.id, puesto_id=puesto.id),
            ProgramaPuesto(programa_id=prog_b.id, puesto_id=puesto.id),
            PlanCurso(plan_id=plan_a.id, curso_id=curso.id, orden=1),
            PlanCurso(plan_id=plan_b.id, curso_id=curso.id, orden=1),
        ])

        enc = EncuentroCapacitacion(
            empresa_id=emp.id,
            plan_id=plan_a.id,
            programa_id=prog_a.id,
            curso_id=curso.id,
            titulo="Sesión multi",
            fecha=date(2026, 4, 1),
            fecha_inicio=datetime(2026, 4, 1, 9, 0),
            estado="planificado",
        )
        db.session.add(enc)
        db.session.flush()
        db.session.add(AsistenciaEncuentro(encuentro_id=enc.id, participante_id=persona.id, asistencia="inscripto"))
        db.session.commit()
        enc_id, pid, curso_id = enc.id, persona.id, curso.id

    r = auth_client.put(
        f"/gos/capacitacion/api/encuentros/{enc_id}/cierre",
        json={"personas": [{"participante_id": pid, "asistio": True}]},
    )
    assert r.status_code == 200
    assert r.get_json()["estado"] == "cerrado"

    with app.app_context():
        acrs = Acreditacion.query.filter_by(persona_id=pid, curso_id=curso.id).all()
        assert len(acrs) == 2
        assert all(a.aprobo for a in acrs)


def test_matriz_analitica_filtros_y_vistas(app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        meta = matriz_filtros_metadata(emp.id)
        assert "planes" in meta
        assert "personas" in meta

        cal = matriz_analitica(emp.id, vista="calendario", anio=2026)
        assert cal["vista"] == "calendario"
        assert "data" in cal
        assert "filas" in cal["data"]
        assert len(cal["data"]["filas"]) == 12

        tabla = matriz_analitica(emp.id, vista="tabla", anio=2026)
        assert "filas" in tabla["data"]
        assert "meses" in tabla["data"]


def test_planes_cursos_endpoint(auth_client, app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        prog = ProgramaCapacitacion(empresa_id=emp.id, codigo="PL-1", nombre="Prog Plan", tipo="interno")
        curso = Curso(empresa_id=emp.id, codigo="C-PL", nombre="Curso Plan", horas=2)
        db.session.add_all([prog, curso])
        db.session.flush()
        plan = ProgramaPlan(programa_id=prog.id, nombre="Seguridad", orden=1)
        db.session.add(plan)
        db.session.flush()
        db.session.add(PlanCurso(plan_id=plan.id, curso_id=curso.id, orden=1))
        db.session.commit()
        plan_id = plan.id

    r = auth_client.get(f"/gos/capacitacion/api/planes/{plan_id}/cursos")
    assert r.status_code == 200
    assert len(r.get_json()["cursos"]) == 1
