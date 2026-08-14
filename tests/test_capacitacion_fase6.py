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
        assert "cursos" in meta

        cal = matriz_analitica(emp.id, vista="calendario", anio=2026)
        assert cal["vista"] == "calendario"
        assert "data" in cal
        assert "filas" in cal["data"]
        assert len(cal["data"]["filas"]) == 12
        assert cal["data"].get("dim") == "planes"
        assert cal["data"]["filas"][0]["nombre"] == "Enero"

        cal_cursos = matriz_analitica(emp.id, vista="calendario", anio=2026, dim="cursos")
        assert cal_cursos["data"].get("dim") == "cursos"
        assert len(cal_cursos["data"]["filas"]) == 12

        cal_personas = matriz_analitica(emp.id, vista="calendario", anio=2026, dim="personas")
        assert cal_personas["data"].get("dim") == "personas"
        assert len(cal_personas["data"]["filas"]) == 12

        tabla = matriz_analitica(emp.id, vista="tabla", anio=2026)
        assert "filas" in tabla["data"]
        assert "meses" in tabla["data"]
        assert tabla["data"]["agrupar_por"] == "persona"

        tabla_puesto = matriz_analitica(emp.id, vista="tabla", anio=2026, agrupar_por="puesto")
        assert tabla_puesto["data"]["agrupar_por"] == "puesto"

        tabla_curso = matriz_analitica(emp.id, vista="tabla", anio=2026, agrupar_por="curso")
        assert tabla_curso["data"]["agrupar_por"] == "curso"

        if cal["data"]["filas"]:
            fila = cal["data"]["filas"][0]
            assert "pct_cumpl_prog" in fila
            assert "pct_pend_sin_vencer" in fila


def test_matriz_calendario_cuenta_cursos_y_planes_no_cupos(app):
    """Un curso/plan con varias personas cuenta 1, no N cupos."""
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        curso = Curso(empresa_id=emp.id, codigo="UNI-1", nombre="Curso único", horas=2)
        personas = [
            Participante(empresa_id=emp.id, nombre=f"Persona {i}", legajo=f"9{i:03d}")
            for i in range(3)
        ]
        prog = ProgramaCapacitacion(
            empresa_id=emp.id, codigo="UNI-P", nombre="Prog Único", tipo="interno"
        )
        db.session.add_all([curso, prog, *personas])
        db.session.flush()
        plan = ProgramaPlan(programa_id=prog.id, nombre="Plan Único", orden=1)
        db.session.add(plan)
        db.session.flush()
        db.session.add(PlanCurso(plan_id=plan.id, curso_id=curso.id, orden=1))
        enc = EncuentroCapacitacion(
            empresa_id=emp.id,
            plan_id=plan.id,
            programa_id=prog.id,
            curso_id=curso.id,
            titulo="Sesión única",
            fecha=date(2026, 8, 1),
            fecha_inicio=datetime(2026, 8, 1, 9, 0),
            estado="planificado",
        )
        db.session.add(enc)
        db.session.flush()
        for p in personas:
            db.session.add(
                AsistenciaEncuentro(
                    encuentro_id=enc.id, participante_id=p.id, asistencia="inscripto"
                )
            )
        db.session.commit()

        def agosto(dim: str) -> dict:
            return matriz_analitica(emp.id, vista="calendario", anio=2026, dim=dim)["data"]["filas"][7]

        assert agosto("cursos")["programados"] == 1
        assert agosto("planes")["programados"] == 1
        assert agosto("personas")["programados"] == 3


def test_matriz_calendario_ignora_charlas_puntuales(app):
    """BPC/charlas van al recuadro: no suman al plan, salvo que el curso se incorpore."""
    with app.app_context():
        from gos.models import Empresa
        from gos.modulos.capacitacion.services.buenas_practicas_service import PROGRAMA_BPC_CODIGO

        emp = Empresa.query.first()
        curso_plan = Curso(empresa_id=emp.id, codigo="PLAN-C", nombre="Curso de plan", horas=2)
        curso_bpc = Curso(empresa_id=emp.id, codigo="BPC-C", nombre="Charla puntual", horas=1)
        persona = Participante(empresa_id=emp.id, nombre="Ana Puntual", legajo="8801")
        prog = ProgramaCapacitacion(
            empresa_id=emp.id, codigo="PP-1", nombre="Programa plan", tipo="interno"
        )
        prog_bpc = ProgramaCapacitacion(
            empresa_id=emp.id,
            codigo=PROGRAMA_BPC_CODIGO,
            nombre="Buenas Prácticas Compartidas",
            tipo="interno",
        )
        db.session.add_all([curso_plan, curso_bpc, persona, prog, prog_bpc])
        db.session.flush()
        plan = ProgramaPlan(programa_id=prog.id, nombre="Plan real", orden=1)
        plan_bpc = ProgramaPlan(programa_id=prog_bpc.id, nombre="Charlas", orden=1)
        db.session.add_all([plan, plan_bpc])
        db.session.flush()
        db.session.add(PlanCurso(plan_id=plan.id, curso_id=curso_plan.id, orden=1))
        db.session.add(PlanCurso(plan_id=plan_bpc.id, curso_id=curso_bpc.id, orden=1))
        enc_plan = EncuentroCapacitacion(
            empresa_id=emp.id,
            plan_id=plan.id,
            programa_id=prog.id,
            curso_id=curso_plan.id,
            titulo="Curso de plan",
            fecha=date(2026, 8, 1),
            fecha_inicio=datetime(2026, 8, 1, 9, 0),
            estado="planificado",
        )
        enc_bpc = EncuentroCapacitacion(
            empresa_id=emp.id,
            plan_id=plan_bpc.id,
            programa_id=prog_bpc.id,
            curso_id=curso_bpc.id,
            titulo="BPC — Charla puntual",
            fecha=date(2026, 8, 1),
            fecha_inicio=datetime(2026, 8, 1, 9, 0),
            estado="cerrado",
            es_buenas_practicas=True,
        )
        db.session.add_all([enc_plan, enc_bpc])
        db.session.flush()
        db.session.add_all(
            [
                AsistenciaEncuentro(
                    encuentro_id=enc_plan.id, participante_id=persona.id, asistencia="inscripto"
                ),
                AsistenciaEncuentro(
                    encuentro_id=enc_bpc.id, participante_id=persona.id, asistencia="presente"
                ),
            ]
        )
        db.session.commit()

        def agosto(dim: str) -> dict:
            return matriz_analitica(emp.id, vista="calendario", anio=2026, dim=dim)["data"]["filas"][7]

        assert agosto("cursos")["programados"] == 1
        assert agosto("planes")["programados"] == 1
        assert agosto("cursos")["charlas_puntuales"] == 1
        assert agosto("cursos")["charlas_puntuales"] == agosto("planes")["charlas_puntuales"]

        db.session.add(PlanCurso(plan_id=plan.id, curso_id=curso_bpc.id, orden=2))
        db.session.commit()
        # Incorporar el curso al plan no hace que la charla puntual sume: hay que programarla en el plan.
        assert agosto("cursos")["programados"] == 1

        enc_plan_bpc = EncuentroCapacitacion(
            empresa_id=emp.id,
            plan_id=plan.id,
            programa_id=prog.id,
            curso_id=curso_bpc.id,
            titulo="Curso de plan (ex charla)",
            fecha=date(2026, 8, 1),
            fecha_inicio=datetime(2026, 8, 1, 10, 0),
            estado="planificado",
            es_buenas_practicas=False,
        )
        db.session.add(enc_plan_bpc)
        db.session.flush()
        db.session.add(
            AsistenciaEncuentro(
                encuentro_id=enc_plan_bpc.id, participante_id=persona.id, asistencia="inscripto"
            )
        )
        db.session.commit()
        assert agosto("cursos")["programados"] == 2


def test_matriz_tabla_filtra_por_curso(app):
    """El filtro de curso deja solo las asignaciones de ese curso en la tabla anual."""
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        curso_a = Curso(empresa_id=emp.id, codigo="FIL-A", nombre="Curso filtro A", horas=2)
        curso_b = Curso(empresa_id=emp.id, codigo="FIL-B", nombre="Curso filtro B", horas=2)
        persona = Participante(empresa_id=emp.id, nombre="Filtro Curso", apellido="Test", legajo="7701")
        prog = ProgramaCapacitacion(
            empresa_id=emp.id, codigo="FIL-P", nombre="Prog Filtro", tipo="interno"
        )
        db.session.add_all([curso_a, curso_b, persona, prog])
        db.session.flush()
        plan = ProgramaPlan(programa_id=prog.id, nombre="Plan Filtro", orden=1)
        db.session.add(plan)
        db.session.flush()
        db.session.add_all([
            PlanCurso(plan_id=plan.id, curso_id=curso_a.id, orden=1),
            PlanCurso(plan_id=plan.id, curso_id=curso_b.id, orden=2),
        ])
        for curso in (curso_a, curso_b):
            enc = EncuentroCapacitacion(
                empresa_id=emp.id,
                plan_id=plan.id,
                programa_id=prog.id,
                curso_id=curso.id,
                titulo=curso.nombre,
                fecha=date(2026, 3, 10),
                fecha_inicio=datetime(2026, 3, 10, 9, 0),
                estado="planificado",
            )
            db.session.add(enc)
            db.session.flush()
            db.session.add(
                AsistenciaEncuentro(
                    encuentro_id=enc.id, participante_id=persona.id, asistencia="inscripto"
                )
            )
        db.session.commit()
        cid_a, pid = curso_a.id, persona.id

        tabla = matriz_analitica(emp.id, vista="tabla", anio=2026, persona_ids=[pid])["data"]
        fila = next(f for f in tabla["filas"] if f["id"] == pid)
        assert fila["meses"]["3"]["prog"] == 2

        tabla_a = matriz_analitica(
            emp.id, vista="tabla", anio=2026, persona_ids=[pid], curso_ids=[cid_a]
        )["data"]
        fila_a = next(f for f in tabla_a["filas"] if f["id"] == pid)
        assert fila_a["meses"]["3"]["prog"] == 1

        tabla_cursos = matriz_analitica(
            emp.id, vista="tabla", anio=2026, agrupar_por="curso", persona_ids=[pid]
        )["data"]
        fila_curso_a = next(f for f in tabla_cursos["filas"] if f["id"] == cid_a)
        assert fila_curso_a["meses"]["3"]["prog"] == 1
        ids_cursos = {f["id"] for f in tabla_cursos["filas"]}
        assert cid_a in ids_cursos


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
