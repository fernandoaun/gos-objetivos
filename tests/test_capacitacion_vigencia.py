"""Tests de vigencia de cursos y reprogramación automática."""
from datetime import date

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    Curso,
    Participante,
    PlanCapacitacion,
    PlanCurso,
    ProgramaCapacitacion,
    ProgramaPlan,
    ProgramaPuesto,
    Puesto,
)
from gos.modulos.capacitacion.models.programa import EncuentroCapacitacion
from gos.modulos.capacitacion.models.registro import AsistenciaEncuentro
from gos.modulos.capacitacion.services.acreditacion_service import (
    anterior_habil,
    aplicar_resultado_asistencia,
    calcular_fecha_vencimiento,
    programar_renovacion_vigencia,
)
from gos.modulos.capacitacion.services.config_service import (
    agregar_periodo_vigencia,
    listar_periodos_vigencia,
)


def test_anterior_habil_salta_fin_de_semana():
    # Viernes 10 → jueves 9
    assert anterior_habil(date(2027, 4, 10)) == date(2027, 4, 9)
    # Lunes 12 → viernes 9 (salta sáb/dom)
    assert anterior_habil(date(2027, 4, 12)) == date(2027, 4, 9)


def test_calcular_fecha_vencimiento_con_vigencia():
    curso = Curso(vigencia_meses=12)
    venc = calcular_fecha_vencimiento(True, date(2026, 4, 1), curso)
    assert venc == date(2027, 4, 1)


def test_agregar_periodo_vigencia(app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        iniciales = len(listar_periodos_vigencia(emp.id))
        periodos = agregar_periodo_vigencia(emp.id, 48, "4 años")
        assert len(periodos) == iniciales + 1
        assert any(p["meses"] == 48 for p in periodos)


def test_reprogramacion_tras_aprobacion(app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        puesto = Puesto(empresa_id=emp.id, codigo="VIG-1", nombre="Vigencia Test")
        curso = Curso(
            empresa_id=emp.id,
            codigo="VIG-C1",
            nombre="Curso con vigencia",
            horas=2,
            vigencia_meses=12,
            requiere_evaluacion=False,
        )
        persona = Participante(empresa_id=emp.id, nombre="Renov Test", legajo="V9001")
        db.session.add_all([puesto, curso, persona])
        db.session.flush()
        persona.puesto_id = puesto.id

        programa = ProgramaCapacitacion(
            empresa_id=emp.id, codigo="PV", nombre="Prog Vig", tipo="interno"
        )
        db.session.add(programa)
        db.session.flush()
        plan = ProgramaPlan(programa_id=programa.id, nombre="Plan", orden=1)
        db.session.add(plan)
        db.session.flush()
        db.session.add_all([
            ProgramaPuesto(programa_id=programa.id, puesto_id=puesto.id),
            PlanCurso(plan_id=plan.id, curso_id=curso.id, orden=1),
        ])

        fecha_dictado = date(2026, 4, 1)
        enc = EncuentroCapacitacion(
            empresa_id=emp.id,
            plan_id=plan.id,
            programa_id=programa.id,
            curso_id=curso.id,
            titulo="Dictado",
            fecha=fecha_dictado,
            estado="en_curso",
        )
        db.session.add(enc)
        db.session.flush()
        asist = AsistenciaEncuentro(
            encuentro_id=enc.id, participante_id=persona.id, asistencia="inscripto"
        )
        db.session.add(asist)
        db.session.commit()

        aplicar_resultado_asistencia(emp.id, enc, asist, asistio=True, nota=None)
        db.session.commit()

        fecha_venc = calcular_fecha_vencimiento(True, fecha_dictado, curso)
        fecha_renov = anterior_habil(fecha_venc)

        plan_persona = PlanCapacitacion.query.filter_by(
            participante_id=persona.id, curso_id=curso.id, empresa_id=emp.id
        ).first()
        assert plan_persona is not None
        assert plan_persona.fecha_planificada == fecha_renov
        assert plan_persona.encuentro_id is not None

        renov_enc = EncuentroCapacitacion.query.get(plan_persona.encuentro_id)
        assert renov_enc.fecha == fecha_renov
        assert renov_enc.estado == "planificado"
