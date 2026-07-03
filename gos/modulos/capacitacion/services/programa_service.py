from __future__ import annotations

from datetime import date, datetime, time

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    AlertaCapacitacion,
    AsistenciaEncuentro,
    CronogramaPuesto,
    Curso,
    EmpresaCapacitadora,
    EncuentroCapacitacion,
    EncuentroTema,
    Instructor,
    InscripcionPrograma,
    Participante,
    PlanCapacitacion,
    PlanCurso,
    ProgramaCapacitacion,
    ProgramaPlan,
    ProgramaPuesto,
    Puesto,
)
from gos.modulos.capacitacion.models.programa import (
    ALCANCES_PROGRAMA,
    ESTADOS_ENCUENTRO,
    ESTADOS_PROGRAMA,
    TIPOS_PROGRAMA,
)
from gos.modulos.capacitacion.services.acreditacion_service import (
    aplicar_resultado_asistencia,
    calcular_fecha_fin,
    cursos_requeridos_por_puesto,
)

RESULTADOS_ASISTENCIA = ("inscripto", "presente", "ausente", "justificado")


def listar_programas(
    empresa_id: int,
    *,
    puesto_id: int | None = None,
    participante_id: int | None = None,
    tipo: str | None = None,
    detalle: bool = False,
) -> list[dict]:
    q = ProgramaCapacitacion.query.filter_by(empresa_id=empresa_id, activo=True)

    if tipo:
        q = q.filter_by(tipo=tipo.strip().lower())

    if puesto_id:
        ids = db.session.query(ProgramaPuesto.programa_id).filter_by(puesto_id=puesto_id)
        q = q.filter(
            db.or_(
                ProgramaCapacitacion.id.in_(ids),
                ProgramaCapacitacion.puesto_id == puesto_id,
            )
        )
    elif participante_id:
        participante = Participante.query.filter_by(
            id=participante_id, empresa_id=empresa_id, activo=True
        ).first()
        if not participante:
            return []

        inscritos = db.session.query(InscripcionPrograma.programa_id).filter_by(
            participante_id=participante_id
        )
        condiciones = [ProgramaCapacitacion.id.in_(inscritos)]
        if participante.puesto_id:
            por_puesto = db.session.query(ProgramaPuesto.programa_id).filter_by(
                puesto_id=participante.puesto_id
            )
            condiciones.append(ProgramaCapacitacion.id.in_(por_puesto))
            condiciones.append(ProgramaCapacitacion.puesto_id == participante.puesto_id)
        q = q.filter(db.or_(*condiciones))

    items = q.order_by(ProgramaCapacitacion.nombre).all()
    return [_programa_dict(p, detalle=detalle) for p in items]


def obtener_programa(empresa_id: int, programa_id: int) -> dict:
    programa = ProgramaCapacitacion.query.filter_by(
        id=programa_id, empresa_id=empresa_id, activo=True
    ).first()
    if not programa:
        raise ValueError("Programa no encontrado")
    return _programa_dict(programa, detalle=True)


def crear_programa(empresa_id: int, data: dict) -> dict:
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre es obligatorio")

    codigo = (data.get("codigo") or "").strip()
    if not codigo:
        base = "".join(ch for ch in nombre.upper() if ch.isalnum())[:12] or "PROG"
        codigo = base
        n = 1
        while ProgramaCapacitacion.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
            codigo = f"{base}{n}"
            n += 1
    elif ProgramaCapacitacion.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe un programa con el código «{codigo}»")

    tipo = (data.get("tipo") or "interno").strip().lower()
    if tipo not in TIPOS_PROGRAMA:
        raise ValueError("Tipo de programa inválido (interno/externo)")

    estado = (data.get("estado") or "programado").strip().lower()
    if estado not in ESTADOS_PROGRAMA:
        raise ValueError("Estado de programa inválido")

    puesto_ids = _parse_id_list(data.get("puesto_ids") or data.get("puestos"))
    puesto_id = data.get("puesto_id") or None
    if puesto_id and int(puesto_id) not in puesto_ids:
        puesto_ids.append(int(puesto_id))

    alcance = (data.get("alcance") or ("puesto" if puesto_ids else "general")).strip().lower()
    if alcance not in ALCANCES_PROGRAMA:
        raise ValueError("Alcance de programa inválido")

    for pid in puesto_ids:
        if not Puesto.query.filter_by(id=pid, empresa_id=empresa_id, activo=True).first():
            raise ValueError(f"Puesto {pid} no encontrado")

    programa = ProgramaCapacitacion(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        tipo=tipo,
        descripcion=(data.get("descripcion") or "").strip() or None,
        sector_id=data.get("sector_id") or None,
        puesto_id=puesto_ids[0] if puesto_ids else None,
        curso_id=data.get("curso_id") or None,
        alcance=alcance,
        fecha_inicio=_parse_date(data.get("fecha_inicio")),
        fecha_fin=_parse_date(data.get("fecha_fin")),
        instructor=(data.get("instructor") or "").strip() or None,
        estado=estado,
    )
    db.session.add(programa)
    db.session.flush()

    _sync_puestos(programa, puesto_ids)

    planes_data = data.get("planes")
    if planes_data:
        _sync_planes(empresa_id, programa, planes_data)
    else:
        plan_nombre = (data.get("plan_inicial") or "General").strip() or "General"
        db.session.add(ProgramaPlan(programa_id=programa.id, nombre=plan_nombre, orden=1))

    db.session.commit()
    return _programa_dict(programa, detalle=True)


def actualizar_programa(empresa_id: int, programa_id: int, data: dict) -> dict:
    programa = ProgramaCapacitacion.query.filter_by(
        id=programa_id, empresa_id=empresa_id, activo=True
    ).first()
    if not programa:
        raise ValueError("Programa no encontrado")

    if "nombre" in data:
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            raise ValueError("El nombre es obligatorio")
        programa.nombre = nombre
    if "descripcion" in data:
        programa.descripcion = (data.get("descripcion") or "").strip() or None
    if "tipo" in data:
        tipo = (data.get("tipo") or "").strip().lower()
        if tipo not in TIPOS_PROGRAMA:
            raise ValueError("Tipo de programa inválido (interno/externo)")
        programa.tipo = tipo
    if "estado" in data:
        estado = (data.get("estado") or "").strip().lower()
        if estado not in ESTADOS_PROGRAMA:
            raise ValueError("Estado de programa inválido")
        programa.estado = estado
    if "activo" in data:
        programa.activo = bool(data["activo"])

    if "puesto_ids" in data or "puestos" in data:
        puesto_ids = _parse_id_list(data.get("puesto_ids") or data.get("puestos"))
        for pid in puesto_ids:
            if not Puesto.query.filter_by(id=pid, empresa_id=empresa_id, activo=True).first():
                raise ValueError(f"Puesto {pid} no encontrado")
        _sync_puestos(programa, puesto_ids)
        programa.puesto_id = puesto_ids[0] if puesto_ids else None
        programa.alcance = "puesto" if puesto_ids else "general"

    if "planes" in data:
        _sync_planes(empresa_id, programa, data.get("planes") or [])

    db.session.commit()
    return _programa_dict(programa, detalle=True)


def agregar_plan(empresa_id: int, programa_id: int, data: dict) -> dict:
    programa = ProgramaCapacitacion.query.filter_by(
        id=programa_id, empresa_id=empresa_id, activo=True
    ).first()
    if not programa:
        raise ValueError("Programa no encontrado")
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre del plan es obligatorio")
    max_orden = (
        db.session.query(db.func.max(ProgramaPlan.orden)).filter_by(programa_id=programa_id).scalar()
        or 0
    )
    plan = ProgramaPlan(
        programa_id=programa_id,
        nombre=nombre,
        orden=int(data.get("orden") or max_orden + 1),
    )
    db.session.add(plan)
    db.session.commit()
    return _plan_dict(plan, empresa_id)


def eliminar_plan(empresa_id: int, plan_id: int) -> None:
    plan = (
        ProgramaPlan.query.join(ProgramaCapacitacion)
        .filter(ProgramaPlan.id == plan_id, ProgramaCapacitacion.empresa_id == empresa_id)
        .first()
    )
    if not plan:
        raise ValueError("Plan no encontrado")
    PlanCurso.query.filter_by(plan_id=plan_id).delete(synchronize_session=False)
    db.session.delete(plan)
    db.session.commit()


def agregar_curso_a_plan(empresa_id: int, plan_id: int, curso_id: int) -> dict:
    plan = (
        ProgramaPlan.query.join(ProgramaCapacitacion)
        .filter(ProgramaPlan.id == plan_id, ProgramaCapacitacion.empresa_id == empresa_id)
        .first()
    )
    if not plan:
        raise ValueError("Plan no encontrado")
    curso = Curso.query.filter_by(id=curso_id, empresa_id=empresa_id, activo=True).first()
    if not curso:
        raise ValueError("Curso no válido")
    if PlanCurso.query.filter_by(plan_id=plan_id, curso_id=curso_id).first():
        raise ValueError("El curso ya está en este plan")

    max_orden = (
        db.session.query(db.func.max(PlanCurso.orden)).filter_by(plan_id=plan_id).scalar() or 0
    )
    pc = PlanCurso(plan_id=plan_id, curso_id=curso_id, orden=max_orden + 1)
    db.session.add(pc)

    # Mantener requisitos legados sincronizados por puesto
    for pp in ProgramaPuesto.query.filter_by(programa_id=plan.programa_id).all():
        _ensure_requisito(empresa_id, pp.puesto_id, curso_id)

    db.session.commit()
    return _plan_curso_dict(pc, empresa_id)


def eliminar_curso_de_plan(empresa_id: int, plan_curso_id: int) -> None:
    pc = (
        PlanCurso.query.join(ProgramaPlan)
        .join(ProgramaCapacitacion)
        .filter(PlanCurso.id == plan_curso_id, ProgramaCapacitacion.empresa_id == empresa_id)
        .first()
    )
    if not pc:
        raise ValueError("Curso del plan no encontrado")
    db.session.delete(pc)
    db.session.commit()


def cursos_de_puestos(empresa_id: int, puesto_ids: list[int]) -> list[dict]:
    return cursos_requeridos_por_puesto(empresa_id, puesto_ids)


def crear_encuentro(empresa_id: int, data: dict) -> dict:
    fecha = _parse_date(data.get("fecha") or data.get("fecha_inicio"))
    curso_id = data.get("curso_id") or None
    participante_ids = _parse_id_list(data.get("participante_ids"))
    puesto_ids = _parse_id_list(data.get("puesto_ids"))

    if not fecha:
        raise ValueError("La fecha es obligatoria")
    if not curso_id:
        raise ValueError("El curso es obligatorio")
    if not participante_ids:
        raise ValueError("Seleccioná al menos una persona")

    curso = Curso.query.filter_by(id=curso_id, empresa_id=empresa_id, activo=True).first()
    if not curso:
        raise ValueError("Curso no válido")

    plan_id = data.get("plan_id") or None
    programa_id = data.get("programa_id") or None
    if plan_id:
        plan = (
            ProgramaPlan.query.join(ProgramaCapacitacion)
            .filter(ProgramaPlan.id == plan_id, ProgramaCapacitacion.empresa_id == empresa_id)
            .first()
        )
        if not plan:
            raise ValueError("Plan no válido")
        programa_id = plan.programa_id

    titulo = (data.get("titulo") or "").strip() or f"{curso.codigo} — {curso.nombre}"

    estado = (data.get("estado") or "planificado").strip().lower()
    if estado == "programado":
        estado = "planificado"
    if estado not in ESTADOS_ENCUENTRO:
        raise ValueError("Estado de encuentro inválido")

    origen = (data.get("origen") or data.get("tipo") or curso.origen or "").strip().lower() or None
    if origen == "externo":
        origen = "externa"
    if origen == "interno":
        origen = "interna"
    empresa_cap_id = data.get("empresa_capacitadora_id") or data.get("empresa_externa_id") or None
    if origen == "externa":
        if not empresa_cap_id:
            raise ValueError("Seleccioná la empresa capacitadora para origen externo")
        if not EmpresaCapacitadora.query.filter_by(
            id=empresa_cap_id, empresa_id=empresa_id, activo=True
        ).first():
            raise ValueError("Empresa capacitadora no válida")
    else:
        empresa_cap_id = None

    instructor_id = data.get("instructor_id") or None
    instructor_nombre = (data.get("instructor") or data.get("capacitador") or "").strip() or None
    if instructor_id:
        inst = Instructor.query.filter_by(id=instructor_id, empresa_id=empresa_id, activo=True).first()
        if not inst:
            raise ValueError("Capacitador no válido")
        instructor_nombre = inst.nombre

    participantes_validos: list[int] = []
    for pid in participante_ids:
        if Participante.query.filter_by(id=pid, empresa_id=empresa_id, activo=True).first():
            participantes_validos.append(pid)
    if not participantes_validos:
        raise ValueError("Ninguna persona seleccionada es válida")

    hora_inicio = _parse_time(data.get("hora_inicio"))
    hora_fin = _parse_time(data.get("hora_fin"))
    fecha_inicio_dt = _combine_datetime(fecha, hora_inicio)
    fecha_fin_dt = _parse_datetime(data.get("fecha_fin"))
    if fecha_fin_dt is None and fecha_inicio_dt is not None:
        fecha_fin_dt = calcular_fecha_fin(fecha_inicio_dt, curso.horas)
        if fecha_fin_dt and not hora_fin:
            hora_fin = fecha_fin_dt.time()

    encuentro = EncuentroCapacitacion(
        empresa_id=empresa_id,
        programa_id=programa_id,
        plan_id=int(plan_id) if plan_id else None,
        curso_id=curso_id,
        numero=data.get("numero"),
        titulo=titulo,
        fecha=fecha,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        fecha_inicio=fecha_inicio_dt,
        fecha_fin=fecha_fin_dt,
        lugar=(data.get("lugar") or "").strip() or None,
        link_virtual=(data.get("link_virtual") or data.get("link") or "").strip() or None,
        instructor=instructor_nombre,
        instructor_id=int(instructor_id) if instructor_id else None,
        origen=origen,
        empresa_capacitadora_id=int(empresa_cap_id) if empresa_cap_id else None,
        estado=estado,
        observaciones=(data.get("observaciones") or "").strip() or None,
    )
    db.session.add(encuentro)
    db.session.flush()

    for pid in puesto_ids:
        if Puesto.query.filter_by(id=pid, empresa_id=empresa_id, activo=True).first():
            db.session.add(CronogramaPuesto(encuentro_id=encuentro.id, puesto_id=pid))

    for pid in participantes_validos:
        db.session.add(
            AsistenciaEncuentro(
                encuentro_id=encuentro.id,
                participante_id=pid,
                asistencia="inscripto",
            )
        )

    db.session.commit()
    return _encuentro_dict(encuentro)


def actualizar_encuentro(empresa_id: int, encuentro_id: int, data: dict) -> dict:
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Encuentro no encontrado")

    if "titulo" in data:
        enc.titulo = (data["titulo"] or "").strip()
    if "fecha" in data:
        enc.fecha = _parse_date(data["fecha"])
    if "hora_inicio" in data:
        enc.hora_inicio = _parse_time(data.get("hora_inicio"))
    if "hora_fin" in data:
        enc.hora_fin = _parse_time(data.get("hora_fin"))
    if "lugar" in data:
        enc.lugar = (data.get("lugar") or "").strip() or None
    if "link_virtual" in data:
        enc.link_virtual = (data.get("link_virtual") or "").strip() or None
    if "instructor" in data:
        enc.instructor = (data.get("instructor") or "").strip() or None
    if "instructor_id" in data:
        instructor_id = data.get("instructor_id") or None
        enc.instructor_id = int(instructor_id) if instructor_id else None
        if enc.instructor_id:
            inst = Instructor.query.filter_by(id=enc.instructor_id, empresa_id=empresa_id, activo=True).first()
            if inst:
                enc.instructor = inst.nombre
    if "origen" in data:
        enc.origen = (data.get("origen") or "").strip().lower() or None
    if "empresa_capacitadora_id" in data:
        enc.empresa_capacitadora_id = data.get("empresa_capacitadora_id") or None
    if "estado" in data:
        estado = (data["estado"] or "").strip().lower()
        if estado not in ESTADOS_ENCUENTRO:
            raise ValueError("Estado inválido")
        enc.estado = estado
    if "observaciones" in data:
        enc.observaciones = (data.get("observaciones") or "").strip() or None

    if "curso_id" in data:
        curso_id = data.get("curso_id") or None
        if not curso_id:
            raise ValueError("El curso es obligatorio")
        curso = Curso.query.filter_by(id=curso_id, empresa_id=empresa_id, activo=True).first()
        if not curso:
            raise ValueError("Curso no válido")
        enc.curso_id = int(curso_id)

    if "participante_ids" in data:
        participante_ids = data.get("participante_ids") or []
        if isinstance(participante_ids, str):
            participante_ids = [int(x) for x in participante_ids.split(",") if str(x).strip().isdigit()]
        else:
            participante_ids = [int(x) for x in participante_ids if x]
        if not participante_ids:
            raise ValueError("Seleccioná al menos una persona")

        participantes_validos: list[int] = []
        for pid in participante_ids:
            if Participante.query.filter_by(id=pid, empresa_id=empresa_id, activo=True).first():
                participantes_validos.append(pid)
        if not participantes_validos:
            raise ValueError("Ninguna persona seleccionada es válida")

        nuevos = set(participantes_validos)
        actuales = {a.participante_id for a in enc.asistencias.all()}
        for pid in actuales - nuevos:
            AsistenciaEncuentro.query.filter_by(encuentro_id=encuentro_id, participante_id=pid).delete(
                synchronize_session=False
            )
        for pid in nuevos - actuales:
            db.session.add(
                AsistenciaEncuentro(
                    encuentro_id=encuentro_id,
                    participante_id=pid,
                    asistencia="inscripto",
                )
            )

    db.session.commit()
    return _encuentro_dict(enc)


def eliminar_encuentro(empresa_id: int, encuentro_id: int) -> dict:
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Encuentro no encontrado")

    AlertaCapacitacion.query.filter_by(encuentro_id=encuentro_id).delete(synchronize_session=False)
    PlanCapacitacion.query.filter_by(encuentro_id=encuentro_id).update(
        {"encuentro_id": None}, synchronize_session=False
    )
    AsistenciaEncuentro.query.filter_by(encuentro_id=encuentro_id).delete(synchronize_session=False)
    EncuentroTema.query.filter_by(encuentro_id=encuentro_id).delete(synchronize_session=False)
    db.session.delete(enc)
    db.session.commit()
    return {"id": encuentro_id, "eliminado": True}


def inscribir_participantes(empresa_id: int, programa_id: int, participante_ids: list[int]) -> dict:
    programa = ProgramaCapacitacion.query.filter_by(id=programa_id, empresa_id=empresa_id).first()
    if not programa:
        raise ValueError("Programa no encontrado")

    inscriptos = 0
    for pid in participante_ids:
        if not Participante.query.filter_by(id=pid, empresa_id=empresa_id, activo=True).first():
            continue
        existe = InscripcionPrograma.query.filter_by(programa_id=programa_id, participante_id=pid).first()
        if existe:
            continue
        db.session.add(
            InscripcionPrograma(
                programa_id=programa_id,
                participante_id=pid,
                fecha_inscripcion=date.today(),
                estado="inscripto",
            )
        )
        inscriptos += 1
    db.session.commit()
    return {"inscriptos": inscriptos}


def registrar_asistencias(empresa_id: int, encuentro_id: int, registros: list[dict]) -> dict:
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Encuentro no encontrado")

    if not registros:
        raise ValueError("Registrá la asistencia de al menos una persona")

    guardados = 0
    for item in registros:
        pid = item.get("participante_id")
        if not pid:
            continue
        asistencia = (item.get("asistencia") or "").strip().lower()
        asistio = item.get("asistio")
        if asistio is None and asistencia:
            if asistencia not in RESULTADOS_ASISTENCIA:
                raise ValueError(f"Asistencia inválida: {asistencia}")
            asistio = asistencia == "presente"
            if asistencia == "inscripto":
                asistio = None

        nota = item.get("nota")
        if nota is not None and nota != "":
            nota = float(nota)
        else:
            nota = None

        row = AsistenciaEncuentro.query.filter_by(encuentro_id=encuentro_id, participante_id=pid).first()
        if not row:
            row = AsistenciaEncuentro(encuentro_id=encuentro_id, participante_id=pid)
            db.session.add(row)
            db.session.flush()

        if asistio is not None:
            aplicar_resultado_asistencia(empresa_id, enc, row, asistio=asistio, nota=nota)
        else:
            row.asistencia = asistencia or "inscripto"
            row.nota = nota
            row.observaciones = (item.get("observaciones") or "").strip() or None

        if item.get("observaciones") is not None:
            row.observaciones = (item.get("observaciones") or "").strip() or None
        guardados += 1

    if guardados == 0:
        raise ValueError("Registrá la asistencia de al menos una persona")

    if enc.estado in ("programado", "planificado", "en_curso"):
        enc.estado = "cerrado"
    db.session.commit()
    return {"guardados": guardados, "estado": enc.estado}


def cerrar_cronograma(empresa_id: int, encuentro_id: int, data: dict) -> dict:
    """Cierre post-evento: asistencia + acreditaciones (reglas 2, 3 y 4)."""
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Encuentro no encontrado")

    registros = data.get("personas") or data.get("registros") or []
    if not registros:
        raise ValueError("Un cronograma no puede cerrarse sin registrar asistencia de al menos una persona")

    if "capacitador" in data or "instructor" in data:
        enc.instructor = (data.get("capacitador") or data.get("instructor") or "").strip() or None
    if "lugar" in data:
        enc.lugar = (data.get("lugar") or "").strip() or None
    if "link" in data or "link_virtual" in data:
        enc.link_virtual = (data.get("link") or data.get("link_virtual") or "").strip() or None
    if "material_adjunto_url" in data:
        enc.material_adjunto_url = (data.get("material_adjunto_url") or "").strip() or None
    if "resultados_adjunto_url" in data:
        enc.resultados_adjunto_url = (data.get("resultados_adjunto_url") or "").strip() or None

    result = registrar_asistencias(empresa_id, encuentro_id, registros)
    enc.estado = "cerrado"
    db.session.commit()
    detalle = detalle_encuentro(empresa_id, encuentro_id)
    detalle["guardados"] = result["guardados"]
    return detalle


def participantes_encuentro(empresa_id: int, encuentro_id: int) -> list[dict]:
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Encuentro no encontrado")

    asistencias = AsistenciaEncuentro.query.filter_by(encuentro_id=encuentro_id).all()
    if asistencias:
        participantes = [a.participante for a in asistencias if a.participante and a.participante.activo]
    elif enc.programa_id:
        inscripciones = InscripcionPrograma.query.filter_by(programa_id=enc.programa_id).all()
        participantes = [i.participante for i in inscripciones if i.participante and i.participante.activo]
    else:
        participantes = (
            Participante.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Participante.nombre).all()
        )

    asist_map = {
        a.participante_id: a
        for a in AsistenciaEncuentro.query.filter_by(encuentro_id=encuentro_id).all()
    }

    resultado = []
    for p in participantes:
        a = asist_map.get(p.id)
        asistencia = a.asistencia if a else None
        aprobado = a.aprobado if a else None
        if aprobado is True:
            estado = "Aprobó"
        elif aprobado is False and asistencia == "ausente":
            estado = "No asistió"
        elif aprobado is False:
            estado = "No aprobó"
        else:
            estado = "Pendiente"
        resultado.append(
            {
                "participante_id": p.id,
                "nombre": p.nombre_completo,
                "legajo": p.legajo,
                "puesto_id": p.puesto_id,
                "tiene_foto": bool(p.foto_path),
                "asistencia": asistencia,
                "asistio": True if asistencia == "presente" else (False if asistencia == "ausente" else None),
                "nota": float(a.nota) if a and a.nota is not None else None,
                "aprobado": aprobado,
                "estado": estado,
                "fecha_aprobacion": a.fecha_aprobacion.isoformat() if a and a.fecha_aprobacion else None,
                "fecha_vencimiento": a.fecha_vencimiento.isoformat() if a and a.fecha_vencimiento else None,
                "observaciones": a.observaciones if a else None,
            }
        )
    return resultado


def detalle_encuentro(empresa_id: int, encuentro_id: int) -> dict:
    enc = EncuentroCapacitacion.query.filter_by(id=encuentro_id, empresa_id=empresa_id).first()
    if not enc:
        raise ValueError("Encuentro no encontrado")
    asistencias = [
        {
            "participante_id": a.participante_id,
            "nombre": a.participante.nombre if a.participante else None,
            "asistencia": a.asistencia,
            "nota": float(a.nota) if a.nota is not None else None,
            "aprobado": a.aprobado,
            "observaciones": a.observaciones,
        }
        for a in AsistenciaEncuentro.query.filter_by(encuentro_id=encuentro_id).all()
    ]
    data = _encuentro_dict(enc)
    data["asistencias"] = asistencias
    data["participantes"] = participantes_encuentro(empresa_id, encuentro_id)
    return data


def _programa_dict(p: ProgramaCapacitacion, *, detalle: bool = False) -> dict:
    puestos = []
    for pp in p.puestos_asignados.all():
        if pp.puesto:
            puestos.append({"id": pp.puesto_id, "nombre": pp.puesto.nombre, "codigo": pp.puesto.codigo})
    if not puestos and p.puesto_id and p.puesto:
        puestos.append({"id": p.puesto_id, "nombre": p.puesto.nombre, "codigo": p.puesto.codigo})

    planes = [_plan_dict(pl, p.empresa_id) for pl in p.planes.all()]
    cursos_count = sum(len(pl["cursos"]) for pl in planes)

    data = {
        "id": p.id,
        "codigo": p.codigo,
        "nombre": p.nombre,
        "descripcion": p.descripcion,
        "tipo": p.tipo or "interno",
        "sector_id": p.sector_id,
        "puesto_id": p.puesto_id,
        "puesto_nombre": puestos[0]["nombre"] if puestos else None,
        "puestos": puestos,
        "puestos_count": len(puestos),
        "planes_count": len(planes),
        "cursos_count": cursos_count,
        "curso_id": p.curso_id,
        "curso_nombre": p.curso.nombre if p.curso else None,
        "alcance": p.alcance or "general",
        "inscriptos": p.inscripciones.count() if p.inscripciones else 0,
        "fecha_inicio": p.fecha_inicio.isoformat() if p.fecha_inicio else None,
        "fecha_fin": p.fecha_fin.isoformat() if p.fecha_fin else None,
        "instructor": p.instructor,
        "estado": p.estado,
        "activo": p.activo,
    }
    if detalle:
        data["planes"] = planes
    return data


def _plan_dict(plan: ProgramaPlan, empresa_id: int) -> dict:
    cursos = [_plan_curso_dict(pc, empresa_id) for pc in plan.cursos.all()]
    return {
        "id": plan.id,
        "programa_id": plan.programa_id,
        "nombre": plan.nombre,
        "orden": plan.orden,
        "cursos": cursos,
        "cursos_count": len(cursos),
    }


def _plan_curso_dict(pc: PlanCurso, empresa_id: int) -> dict:
    curso = pc.curso
    tambien_en = _otros_programas_del_curso(empresa_id, pc.curso_id, pc.plan.programa_id if pc.plan else None)
    return {
        "id": pc.id,
        "plan_id": pc.plan_id,
        "curso_id": pc.curso_id,
        "orden": pc.orden,
        "curso_codigo": curso.codigo if curso else None,
        "curso_nombre": curso.nombre if curso else None,
        "horas": float(curso.horas) if curso and curso.horas is not None else None,
        "origen": curso.origen if curso else None,
        "requiere_evaluacion": curso.requiere_evaluacion if curso else False,
        "tambien_en": tambien_en,
    }


def _otros_programas_del_curso(empresa_id: int, curso_id: int, excluir_programa_id: int | None) -> list[dict]:
    filas = (
        db.session.query(ProgramaCapacitacion)
        .join(ProgramaPlan, ProgramaPlan.programa_id == ProgramaCapacitacion.id)
        .join(PlanCurso, PlanCurso.plan_id == ProgramaPlan.id)
        .filter(
            ProgramaCapacitacion.empresa_id == empresa_id,
            ProgramaCapacitacion.activo.is_(True),
            PlanCurso.curso_id == curso_id,
        )
        .all()
    )
    vistos = set()
    resultado = []
    for prog in filas:
        if prog.id == excluir_programa_id or prog.id in vistos:
            continue
        vistos.add(prog.id)
        resultado.append({"id": prog.id, "nombre": prog.nombre, "tipo": prog.tipo})
    return resultado


def _sync_puestos(programa: ProgramaCapacitacion, puesto_ids: list[int]) -> None:
    actuales = {pp.puesto_id: pp for pp in programa.puestos_asignados.all()}
    nuevos = set(puesto_ids)
    for pid, row in list(actuales.items()):
        if pid not in nuevos:
            db.session.delete(row)
    for pid in nuevos - set(actuales):
        db.session.add(ProgramaPuesto(programa_id=programa.id, puesto_id=pid))


def _sync_planes(empresa_id: int, programa: ProgramaCapacitacion, planes_data: list) -> None:
    actuales = {pl.id: pl for pl in programa.planes.all()}
    vistos = set()
    for idx, item in enumerate(planes_data, start=1):
        plan_id = item.get("id")
        nombre = (item.get("nombre") or "").strip()
        if not nombre:
            continue
        if plan_id and plan_id in actuales:
            plan = actuales[plan_id]
            plan.nombre = nombre
            plan.orden = int(item.get("orden") or idx)
            vistos.add(plan_id)
        else:
            plan = ProgramaPlan(programa_id=programa.id, nombre=nombre, orden=int(item.get("orden") or idx))
            db.session.add(plan)
            db.session.flush()
            vistos.add(plan.id)

        curso_ids = _parse_id_list(item.get("curso_ids") or [c.get("curso_id") for c in item.get("cursos") or []])
        existentes = {pc.curso_id: pc for pc in plan.cursos.all()}
        for orden, cid in enumerate(curso_ids, start=1):
            if not Curso.query.filter_by(id=cid, empresa_id=empresa_id, activo=True).first():
                raise ValueError(f"Curso {cid} no válido")
            if cid in existentes:
                existentes[cid].orden = orden
            else:
                db.session.add(PlanCurso(plan_id=plan.id, curso_id=cid, orden=orden))
                for pp in programa.puestos_asignados.all():
                    _ensure_requisito(empresa_id, pp.puesto_id, cid)
        for cid, pc in list(existentes.items()):
            if cid not in curso_ids:
                db.session.delete(pc)

    for plan_id, plan in actuales.items():
        if plan_id not in vistos:
            PlanCurso.query.filter_by(plan_id=plan_id).delete(synchronize_session=False)
            db.session.delete(plan)


def _ensure_requisito(empresa_id: int, puesto_id: int, curso_id: int) -> None:
    from gos.modulos.capacitacion.models import RequisitoFormacion

    existe = RequisitoFormacion.query.filter_by(
        empresa_id=empresa_id, puesto_id=puesto_id, curso_id=curso_id
    ).first()
    if existe:
        return
    db.session.add(
        RequisitoFormacion(
            empresa_id=empresa_id,
            puesto_id=puesto_id,
            curso_id=curso_id,
            obligatorio=True,
        )
    )


def _parse_id_list(raw) -> list[int]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [int(x) for x in raw.split(",") if str(x).strip().isdigit()]
    result = []
    for x in raw:
        if x is None or x == "":
            continue
        result.append(int(x))
    return result


def _encuentro_dict(e: EncuentroCapacitacion) -> dict:
    curso = e.curso
    emp_cap = e.empresa_capacitadora
    inscriptos = e.asistencias.count() if e.asistencias else 0
    puestos = [
        {"id": cp.puesto_id, "nombre": cp.puesto.nombre if cp.puesto else None}
        for cp in e.puestos_convocados.all()
    ]
    return {
        "id": e.id,
        "titulo": e.titulo,
        "fecha": e.fecha.isoformat() if e.fecha else None,
        "hora_inicio": e.hora_inicio.isoformat() if e.hora_inicio else None,
        "hora_fin": e.hora_fin.isoformat() if e.hora_fin else None,
        "fecha_inicio": e.fecha_inicio.isoformat() if e.fecha_inicio else None,
        "fecha_fin": e.fecha_fin.isoformat() if e.fecha_fin else None,
        "lugar": e.lugar,
        "link_virtual": e.link_virtual,
        "instructor": e.instructor,
        "instructor_id": e.instructor_id,
        "origen": e.origen,
        "tipo": "externo" if (e.origen or "").startswith("extern") else "interno",
        "empresa_capacitadora_id": e.empresa_capacitadora_id,
        "empresa_capacitadora_nombre": emp_cap.nombre if emp_cap else None,
        "estado": e.estado,
        "programa_id": e.programa_id,
        "plan_id": e.plan_id,
        "plan_nombre": e.plan.nombre if e.plan else None,
        "curso_id": e.curso_id,
        "curso_codigo": curso.codigo if curso else None,
        "curso_nombre": curso.nombre if curso else None,
        "curso_horas": float(curso.horas) if curso and curso.horas is not None else None,
        "curso_requiere_evaluacion": curso.requiere_evaluacion if curso else False,
        "curso_puntaje_minimo": float(curso.puntaje_minimo) if curso and curso.puntaje_minimo is not None else None,
        "inscriptos": inscriptos,
        "puestos": puestos,
        "material_adjunto_url": e.material_adjunto_url,
        "resultados_adjunto_url": e.resultados_adjunto_url,
        "observaciones": e.observaciones,
    }


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)
    if "T" in text:
        return datetime.fromisoformat(text.replace("Z", "")).date()
    return date.fromisoformat(text[:10])


def _parse_time(value) -> time | None:
    if not value:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    parts = str(value).split(":")
    return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "")
    if "T" in text:
        return datetime.fromisoformat(text)
    d = _parse_date(text)
    return datetime.combine(d, time(9, 0)) if d else None


def _combine_datetime(d: date | None, t: time | None):
    if not d:
        return None
    return datetime.combine(d, t or time(9, 0))
