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
