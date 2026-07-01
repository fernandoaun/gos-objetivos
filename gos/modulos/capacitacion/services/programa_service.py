from __future__ import annotations

from datetime import date, time

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    AlertaCapacitacion,
    AsistenciaEncuentro,
    Curso,
    EmpresaCapacitadora,
    EncuentroCapacitacion,
    EncuentroTema,
    Instructor,
    InscripcionPrograma,
    Participante,
    PlanCapacitacion,
    ProgramaCapacitacion,
    Puesto,
    RegistroCapacitacion,
)
from gos.modulos.capacitacion.models.programa import (
    ALCANCES_PROGRAMA,
    ESTADOS_ENCUENTRO,
    ESTADOS_PROGRAMA,
)

RESULTADOS_ASISTENCIA = ("inscripto", "presente", "ausente", "justificado")


def listar_programas(
    empresa_id: int,
    *,
    puesto_id: int | None = None,
    participante_id: int | None = None,
) -> list[dict]:
    q = ProgramaCapacitacion.query.filter_by(empresa_id=empresa_id, activo=True)

    if puesto_id:
        q = q.filter(
            db.and_(
                ProgramaCapacitacion.alcance == "puesto",
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
            condiciones.append(
                db.and_(
                    ProgramaCapacitacion.alcance == "puesto",
                    ProgramaCapacitacion.puesto_id == participante.puesto_id,
                )
            )
        q = q.filter(db.or_(*condiciones))

    items = q.order_by(ProgramaCapacitacion.fecha_inicio.desc()).all()
    return [_programa_dict(p) for p in items]


def crear_programa(empresa_id: int, data: dict) -> dict:
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")

    estado = (data.get("estado") or "borrador").strip().lower()
    if estado not in ESTADOS_PROGRAMA:
        raise ValueError("Estado de programa inválido")

    alcance = (data.get("alcance") or "general").strip().lower()
    if alcance not in ALCANCES_PROGRAMA:
        raise ValueError("Alcance de programa inválido")

    puesto_id = data.get("puesto_id") or None
    if alcance == "puesto":
        if not puesto_id:
            raise ValueError("El puesto es obligatorio para programas por puesto")
        if not Puesto.query.filter_by(id=puesto_id, empresa_id=empresa_id, activo=True).first():
            raise ValueError("Puesto no encontrado")
    else:
        puesto_id = None

    programa = ProgramaCapacitacion(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        descripcion=(data.get("descripcion") or "").strip() or None,
        sector_id=data.get("sector_id") or None,
        puesto_id=puesto_id,
        curso_id=data.get("curso_id") or None,
        alcance=alcance,
        fecha_inicio=_parse_date(data.get("fecha_inicio")),
        fecha_fin=_parse_date(data.get("fecha_fin")),
        instructor=(data.get("instructor") or "").strip() or None,
        estado=estado,
    )
    db.session.add(programa)
    db.session.commit()
    return _programa_dict(programa)


def crear_encuentro(empresa_id: int, data: dict) -> dict:
    fecha = _parse_date(data.get("fecha"))
    curso_id = data.get("curso_id") or None
    participante_ids = data.get("participante_ids") or []
    if isinstance(participante_ids, str):
        participante_ids = [int(x) for x in participante_ids.split(",") if str(x).strip().isdigit()]
    else:
        participante_ids = [int(x) for x in participante_ids if x]

    if not fecha:
        raise ValueError("La fecha es obligatoria")
    if not curso_id:
        raise ValueError("El curso es obligatorio")
    if not participante_ids:
        raise ValueError("Seleccioná al menos una persona")

    curso = Curso.query.filter_by(id=curso_id, empresa_id=empresa_id, activo=True).first()
    if not curso:
        raise ValueError("Curso no válido")

    titulo = (data.get("titulo") or "").strip() or f"{curso.codigo} — {curso.nombre}"

    estado = (data.get("estado") or "programado").strip().lower()
    if estado not in ESTADOS_ENCUENTRO:
        raise ValueError("Estado de encuentro inválido")

    origen = (data.get("origen") or curso.origen or "").strip().lower() or None
    empresa_cap_id = data.get("empresa_capacitadora_id") or None
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
    instructor_nombre = (data.get("instructor") or "").strip() or None
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

    encuentro = EncuentroCapacitacion(
        empresa_id=empresa_id,
        programa_id=data.get("programa_id") or None,
        curso_id=curso_id,
        numero=data.get("numero"),
        titulo=titulo,
        fecha=fecha,
        hora_inicio=_parse_time(data.get("hora_inicio")),
        hora_fin=_parse_time(data.get("hora_fin")),
        lugar=(data.get("lugar") or "").strip() or None,
        link_virtual=(data.get("link_virtual") or "").strip() or None,
        instructor=instructor_nombre,
        instructor_id=int(instructor_id) if instructor_id else None,
        origen=origen,
        empresa_capacitadora_id=int(empresa_cap_id) if empresa_cap_id else None,
        estado=estado,
        observaciones=(data.get("observaciones") or "").strip() or None,
    )
    db.session.add(encuentro)
    db.session.flush()

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

    guardados = 0
    for item in registros:
        pid = item.get("participante_id")
        if not pid:
            continue
        asistencia = (item.get("asistencia") or "presente").strip().lower()
        if asistencia not in RESULTADOS_ASISTENCIA:
            raise ValueError(f"Asistencia inválida: {asistencia}")

        row = AsistenciaEncuentro.query.filter_by(encuentro_id=encuentro_id, participante_id=pid).first()
        if not row:
            row = AsistenciaEncuentro(encuentro_id=encuentro_id, participante_id=pid)
            db.session.add(row)
        row.asistencia = asistencia
        if item.get("nota") is not None and item.get("nota") != "":
            row.nota = float(item["nota"])
        if item.get("aprobado") is not None:
            row.aprobado = bool(item["aprobado"])
        row.observaciones = (item.get("observaciones") or "").strip() or None
        guardados += 1

        if enc.curso_id and row.aprobado and asistencia == "presente":
            _crear_registro_desde_asistencia(empresa_id, enc, pid, row)

    if enc.estado == "programado":
        enc.estado = "realizado"
    db.session.commit()
    return {"guardados": guardados}


def _crear_registro_desde_asistencia(
    empresa_id: int, enc: EncuentroCapacitacion, participante_id: int, asist: AsistenciaEncuentro
) -> None:
    from datetime import timedelta

    curso = enc.curso
    vigente_hasta = None
    if curso and curso.vigencia_meses:
        vigente_hasta = enc.fecha + timedelta(days=int(curso.vigencia_meses) * 30)

    reg = RegistroCapacitacion(
        empresa_id=empresa_id,
        participante_id=participante_id,
        curso_id=enc.curso_id,
        programa_id=enc.programa_id,
        fecha_realizacion=enc.fecha,
        nota=asist.nota,
        aprobado=bool(asist.aprobado),
        horas=curso.horas if curso else None,
        vigente_hasta=vigente_hasta,
    )
    db.session.add(reg)


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
        resultado.append(
            {
                "participante_id": p.id,
                "nombre": p.nombre_completo,
                "legajo": p.legajo,
                "puesto_id": p.puesto_id,
                "asistencia": a.asistencia if a else None,
                "nota": float(a.nota) if a and a.nota is not None else None,
                "aprobado": a.aprobado if a else None,
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


def _programa_dict(p: ProgramaCapacitacion) -> dict:
    inscriptos = p.inscripciones.count() if p.inscripciones else 0
    return {
        "id": p.id,
        "codigo": p.codigo,
        "nombre": p.nombre,
        "descripcion": p.descripcion,
        "sector_id": p.sector_id,
        "puesto_id": p.puesto_id,
        "puesto_nombre": p.puesto.nombre if p.puesto else None,
        "curso_id": p.curso_id,
        "curso_nombre": p.curso.nombre if p.curso else None,
        "alcance": p.alcance or "general",
        "inscriptos": inscriptos,
        "fecha_inicio": p.fecha_inicio.isoformat() if p.fecha_inicio else None,
        "fecha_fin": p.fecha_fin.isoformat() if p.fecha_fin else None,
        "instructor": p.instructor,
        "estado": p.estado,
    }


def _encuentro_dict(e: EncuentroCapacitacion) -> dict:
    curso = e.curso
    emp_cap = e.empresa_capacitadora
    inscriptos = e.asistencias.count() if e.asistencias else 0
    return {
        "id": e.id,
        "titulo": e.titulo,
        "fecha": e.fecha.isoformat(),
        "hora_inicio": e.hora_inicio.isoformat() if e.hora_inicio else None,
        "hora_fin": e.hora_fin.isoformat() if e.hora_fin else None,
        "lugar": e.lugar,
        "link_virtual": e.link_virtual,
        "instructor": e.instructor,
        "instructor_id": e.instructor_id,
        "origen": e.origen,
        "empresa_capacitadora_id": e.empresa_capacitadora_id,
        "empresa_capacitadora_nombre": emp_cap.nombre if emp_cap else None,
        "estado": e.estado,
        "programa_id": e.programa_id,
        "curso_id": e.curso_id,
        "curso_codigo": curso.codigo if curso else None,
        "curso_nombre": curso.nombre if curso else None,
        "inscriptos": inscriptos,
        "observaciones": e.observaciones,
    }


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _parse_time(value) -> time | None:
    if not value:
        return None
    if isinstance(value, time):
        return value
    parts = str(value).split(":")
    return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
