"""Reglas de negocio de aprobación, vigencia y acreditación múltiple."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    Acreditacion,
    AsistenciaEncuentro,
    Curso,
    EncuentroCapacitacion,
    Participante,
    PlanCapacitacion,
    PlanCurso,
    ProgramaCapacitacion,
    ProgramaPlan,
    ProgramaPuesto,
    RegistroCapacitacion,
)


def calcular_fecha_fin(fecha_inicio: datetime, duracion_horas: float | Decimal | None) -> datetime | None:
    """fecha_fin = fecha_inicio + duracion_horas, repartiendo en días hábiles (8 hs/día)."""
    if not fecha_inicio or duracion_horas is None:
        return None
    horas = float(duracion_horas)
    if horas <= 0:
        return fecha_inicio

    if horas <= 8:
        return fecha_inicio + timedelta(hours=horas)

    restante = horas
    actual = fecha_inicio
    while restante > 0:
        if actual.weekday() >= 5:  # sábado/domingo
            actual = _siguiente_habil(actual.replace(hour=9, minute=0, second=0, microsecond=0))
            continue
        bloque = min(restante, 8.0)
        actual = actual + timedelta(hours=bloque)
        restante -= bloque
        if restante > 0:
            actual = _siguiente_habil(
                (actual + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            )
    return actual


def _siguiente_habil(dt: datetime) -> datetime:
    while dt.weekday() >= 5:
        dt = dt + timedelta(days=1)
    return dt


def anterior_habil(d: date) -> date:
    """Día hábil (lun-vie) inmediatamente anterior a la fecha indicada."""
    actual = d - timedelta(days=1)
    while actual.weekday() >= 5:
        actual -= timedelta(days=1)
    return actual


def calcular_aprobacion(
    asistio: bool | None,
    nota: float | Decimal | None,
    curso: Curso | None,
) -> bool | None:
    """Regla 2: aprobación automática según asistencia y evaluación del curso."""
    if asistio is None:
        return None
    if not asistio:
        return False
    if not curso or not curso.requiere_evaluacion:
        return True
    if nota is None:
        return False
    minimo = float(curso.puntaje_minimo) if curso.puntaje_minimo is not None else 0
    return float(nota) >= minimo


def calcular_fecha_vencimiento(
    aprobo: bool | None,
    fecha_aprobacion: date | None,
    curso: Curso | None,
) -> date | None:
    """Regla 3: vencimiento según vigencia del curso."""
    if not aprobo or not fecha_aprobacion or not curso:
        return None
    if not curso.tiene_vigencia:
        return None
    return _add_months(fecha_aprobacion, int(curso.vigencia_meses))


def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def programas_planes_del_curso(empresa_id: int, curso_id: int) -> list[tuple[ProgramaCapacitacion, ProgramaPlan]]:
    """Planes (y su programa) donde aparece el curso."""
    filas = (
        db.session.query(ProgramaCapacitacion, ProgramaPlan)
        .join(ProgramaPlan, ProgramaPlan.programa_id == ProgramaCapacitacion.id)
        .join(PlanCurso, PlanCurso.plan_id == ProgramaPlan.id)
        .filter(
            ProgramaCapacitacion.empresa_id == empresa_id,
            ProgramaCapacitacion.activo.is_(True),
            PlanCurso.curso_id == curso_id,
        )
        .all()
    )
    return filas


def persona_tiene_programa(persona: Participante, programa_id: int) -> bool:
    """Un programa aplica a la persona por su puesto."""
    if not persona.puesto_id:
        return False
    return (
        ProgramaPuesto.query.filter_by(programa_id=programa_id, puesto_id=persona.puesto_id).first()
        is not None
    )


def sincronizar_acreditaciones_persona_curso(
    empresa_id: int,
    persona_id: int,
    curso_id: int,
    *,
    aprobo: bool,
    nota: float | Decimal | None,
    fecha_aprobacion: date | None,
    fecha_vencimiento: date | None,
    horas: float | Decimal | None,
    cronograma_persona_id: int | None = None,
) -> list[Acreditacion]:
    """
    Regla 4: al aprobar un curso, acreditar en todos los Programas/Planes
    donde aparece y que aplican al puesto de la persona.
    """
    persona = Participante.query.filter_by(id=persona_id, empresa_id=empresa_id).first()
    if not persona:
        return []

    hoy = date.today()
    vigentes = []
    for programa, plan in programas_planes_del_curso(empresa_id, curso_id):
        if not persona_tiene_programa(persona, programa.id):
            continue

        row = Acreditacion.query.filter_by(
            persona_id=persona_id,
            programa_id=programa.id,
            plan_id=plan.id,
            curso_id=curso_id,
        ).first()
        if not row:
            row = Acreditacion(
                empresa_id=empresa_id,
                persona_id=persona_id,
                programa_id=programa.id,
                plan_id=plan.id,
                curso_id=curso_id,
            )
            db.session.add(row)

        row.aprobo = bool(aprobo)
        row.nota = nota
        row.fecha_aprobacion = fecha_aprobacion if aprobo else None
        row.fecha_vencimiento = fecha_vencimiento if aprobo else None
        row.horas_acreditadas = horas if aprobo else None
        row.cronograma_persona_id = cronograma_persona_id
        row.vigente = bool(
            aprobo and (fecha_vencimiento is None or fecha_vencimiento >= hoy)
        )
        vigentes.append(row)

    return vigentes


def aplicar_resultado_asistencia(
    empresa_id: int,
    encuentro: EncuentroCapacitacion,
    asist: AsistenciaEncuentro,
    *,
    asistio: bool | None,
    nota: float | Decimal | None,
) -> AsistenciaEncuentro:
    """Aplica reglas 2, 3 y 4 sobre un registro de CronogramaPersona."""
    curso = encuentro.curso or (
        Curso.query.filter_by(id=encuentro.curso_id, empresa_id=empresa_id).first()
        if encuentro.curso_id
        else None
    )

    asist.nota = nota
    if asistio is True:
        asist.asistencia = "presente"
    elif asistio is False:
        asist.asistencia = "ausente"
    # asistio None deja el valor previo / inscripto

    aprobo = calcular_aprobacion(asistio, nota, curso)
    asist.aprobado = aprobo

    fecha_aprob = None
    fecha_venc = None
    if aprobo:
        fecha_aprob = encuentro.fecha or date.today()
        fecha_venc = calcular_fecha_vencimiento(True, fecha_aprob, curso)
    asist.fecha_aprobacion = fecha_aprob
    asist.fecha_vencimiento = fecha_venc

    if encuentro.curso_id and asistio is not None:
        sincronizar_acreditaciones_persona_curso(
            empresa_id,
            asist.participante_id,
            encuentro.curso_id,
            aprobo=bool(aprobo),
            nota=nota,
            fecha_aprobacion=fecha_aprob,
            fecha_vencimiento=fecha_venc,
            horas=curso.horas if curso and aprobo else None,
            cronograma_persona_id=asist.id,
        )
        if aprobo:
            _upsert_registro(empresa_id, encuentro, asist, curso)
            if fecha_venc:
                programar_renovacion_vigencia(empresa_id, encuentro, asist, curso, fecha_venc)

    return asist


def programar_renovacion_vigencia(
    empresa_id: int,
    encuentro: EncuentroCapacitacion,
    asist: AsistenciaEncuentro,
    curso: Curso,
    fecha_venc: date,
) -> dict | None:
    """Programa renovación el día hábil previo al vencimiento."""
    if not fecha_venc or not curso.tiene_vigencia or not encuentro.curso_id:
        return None

    fecha_renov = anterior_habil(fecha_venc)
    if fecha_renov <= date.today():
        return None

    participante_id = asist.participante_id
    curso_id = encuentro.curso_id

    renov_enc = _buscar_o_crear_encuentro_renovacion(empresa_id, encuentro, curso, fecha_renov)

    plan = (
        PlanCapacitacion.query.filter_by(
            empresa_id=empresa_id,
            participante_id=participante_id,
            curso_id=curso_id,
        )
        .filter(PlanCapacitacion.estado.in_(("pendiente", "programado")))
        .first()
    )

    obs = "Renovación automática por vencimiento"
    if plan:
        if not plan.fecha_planificada or plan.fecha_planificada > fecha_renov:
            plan.fecha_planificada = fecha_renov
        if renov_enc:
            plan.encuentro_id = renov_enc.id
            plan.estado = "programado"
        if not plan.observaciones:
            plan.observaciones = obs
        if renov_enc:
            _inscribir_en_renovacion(renov_enc, participante_id)
        return {
            "plan_id": plan.id,
            "encuentro_id": renov_enc.id if renov_enc else None,
            "fecha": fecha_renov.isoformat(),
        }

    plan = PlanCapacitacion(
        empresa_id=empresa_id,
        participante_id=participante_id,
        curso_id=curso_id,
        programa_id=encuentro.programa_id,
        encuentro_id=renov_enc.id if renov_enc else None,
        fecha_planificada=fecha_renov,
        estado="programado" if renov_enc else "pendiente",
        prioridad=2,
        observaciones=obs,
    )
    db.session.add(plan)
    if renov_enc:
        _inscribir_en_renovacion(renov_enc, participante_id)
    return {
        "plan_id": plan.id,
        "encuentro_id": renov_enc.id if renov_enc else None,
        "fecha": fecha_renov.isoformat(),
    }


def _buscar_o_crear_encuentro_renovacion(
    empresa_id: int,
    encuentro: EncuentroCapacitacion,
    curso: Curso,
    fecha_renov: date,
) -> EncuentroCapacitacion | None:
    if not encuentro.programa_id:
        return None

    tag = f"renovacion_auto:{encuentro.id}"
    existing = EncuentroCapacitacion.query.filter_by(
        empresa_id=empresa_id,
        curso_id=encuentro.curso_id,
        programa_id=encuentro.programa_id,
        plan_id=encuentro.plan_id,
        fecha=fecha_renov,
        estado="planificado",
    ).first()
    if existing:
        return existing

    nuevo = EncuentroCapacitacion(
        empresa_id=empresa_id,
        programa_id=encuentro.programa_id,
        plan_id=encuentro.plan_id,
        curso_id=encuentro.curso_id,
        titulo=f"Renovación: {curso.nombre}",
        fecha=fecha_renov,
        hora_inicio=encuentro.hora_inicio,
        hora_fin=encuentro.hora_fin,
        lugar=encuentro.lugar,
        link_virtual=encuentro.link_virtual,
        instructor=encuentro.instructor,
        instructor_id=encuentro.instructor_id,
        origen=encuentro.origen,
        empresa_capacitadora_id=encuentro.empresa_capacitadora_id,
        estado="planificado",
        observaciones=f"{tag} — programado automáticamente",
    )
    db.session.add(nuevo)
    db.session.flush()
    return nuevo


def _inscribir_en_renovacion(encuentro: EncuentroCapacitacion, participante_id: int) -> None:
    existe = AsistenciaEncuentro.query.filter_by(
        encuentro_id=encuentro.id,
        participante_id=participante_id,
    ).first()
    if not existe:
        db.session.add(
            AsistenciaEncuentro(
                encuentro_id=encuentro.id,
                participante_id=participante_id,
                asistencia="inscripto",
            )
        )


def _upsert_registro(
    empresa_id: int,
    encuentro: EncuentroCapacitacion,
    asist: AsistenciaEncuentro,
    curso: Curso | None,
) -> None:
    existente = (
        RegistroCapacitacion.query.filter_by(
            participante_id=asist.participante_id,
            curso_id=encuentro.curso_id,
            fecha_realizacion=encuentro.fecha,
        )
        .order_by(RegistroCapacitacion.id.desc())
        .first()
    )
    if existente:
        existente.nota = asist.nota
        existente.aprobado = bool(asist.aprobado)
        existente.vigente_hasta = asist.fecha_vencimiento
        existente.horas = curso.horas if curso else existente.horas
        existente.programa_id = encuentro.programa_id
        return

    db.session.add(
        RegistroCapacitacion(
            empresa_id=empresa_id,
            participante_id=asist.participante_id,
            curso_id=encuentro.curso_id,
            programa_id=encuentro.programa_id,
            fecha_realizacion=encuentro.fecha,
            nota=asist.nota,
            aprobado=bool(asist.aprobado),
            horas=curso.horas if curso else None,
            vigente_hasta=asist.fecha_vencimiento,
        )
    )


def refrescar_vigencias(empresa_id: int) -> int:
    """Marca acreditaciones vencidas (regla 5)."""
    hoy = date.today()
    rows = Acreditacion.query.filter_by(empresa_id=empresa_id, vigente=True).all()
    n = 0
    for row in rows:
        if row.fecha_vencimiento and row.fecha_vencimiento < hoy:
            row.vigente = False
            n += 1
    if n:
        db.session.commit()
    return n


def cursos_requeridos_por_puesto(empresa_id: int, puesto_ids: list[int]) -> list[dict]:
    """Cursos de todos los programas que aplican a los puestos indicados."""
    if not puesto_ids:
        return []

    filas = (
        db.session.query(PlanCurso, ProgramaPlan, ProgramaCapacitacion, Curso)
        .join(ProgramaPlan, ProgramaPlan.id == PlanCurso.plan_id)
        .join(ProgramaCapacitacion, ProgramaCapacitacion.id == ProgramaPlan.programa_id)
        .join(ProgramaPuesto, ProgramaPuesto.programa_id == ProgramaCapacitacion.id)
        .join(Curso, Curso.id == PlanCurso.curso_id)
        .filter(
            ProgramaCapacitacion.empresa_id == empresa_id,
            ProgramaCapacitacion.activo.is_(True),
            ProgramaPuesto.puesto_id.in_(puesto_ids),
            Curso.activo.is_(True),
        )
        .order_by(ProgramaCapacitacion.nombre, ProgramaPlan.orden, PlanCurso.orden)
        .all()
    )

    vistos: set[int] = set()
    resultado = []
    for pc, plan, programa, curso in filas:
        if curso.id in vistos:
            continue
        vistos.add(curso.id)
        resultado.append(
            {
                "id": pc.id,
                "curso_id": curso.id,
                "curso_codigo": curso.codigo,
                "curso_nombre": curso.nombre,
                "plan_id": plan.id,
                "plan_nombre": plan.nombre,
                "programa_id": programa.id,
                "programa_nombre": programa.nombre,
                "programa_tipo": programa.tipo,
                "horas": float(curso.horas) if curso.horas is not None else None,
                "requiere_evaluacion": curso.requiere_evaluacion,
                "puntaje_minimo": float(curso.puntaje_minimo) if curso.puntaje_minimo is not None else None,
                "origen": curso.origen,
            }
        )
    return resultado


def cursos_requeridos_persona(persona: Participante) -> list[dict]:
    if not persona.puesto_id:
        return []
    return cursos_requeridos_por_puesto(persona.empresa_id, [persona.puesto_id])
