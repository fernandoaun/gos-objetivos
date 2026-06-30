from __future__ import annotations

from datetime import date, time

from gos.extensions import db
from gos.modulos.capacitacion.models import (
    AsistenciaEncuentro,
    EncuentroCapacitacion,
    InscripcionPrograma,
    Participante,
    ProgramaCapacitacion,
    Puesto,
    RegistroCapacitacion,
)
from gos.modulos.capacitacion.models.programa import (
    ALCANCES_PROGRAMA,
    ESTADOS_ENCUENTRO,
    ESTADOS_PROGRAMA,
)

RESULTADOS_ASISTENCIA = ("presente", "ausente", "justificado")


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
    titulo = (data.get("titulo") or "").strip()
    fecha = _parse_date(data.get("fecha"))
    if not titulo or not fecha:
        raise ValueError("Título y fecha son obligatorios")

    estado = (data.get("estado") or "programado").strip().lower()
    if estado not in ESTADOS_ENCUENTRO:
        raise ValueError("Estado de encuentro inválido")

    encuentro = EncuentroCapacitacion(
        empresa_id=empresa_id,
        programa_id=data.get("programa_id") or None,
        curso_id=data.get("curso_id") or None,
        numero=data.get("numero"),
        titulo=titulo,
        fecha=fecha,
        hora_inicio=_parse_time(data.get("hora_inicio")),
        hora_fin=_parse_time(data.get("hora_fin")),
        lugar=(data.get("lugar") or "").strip() or None,
        link_virtual=(data.get("link_virtual") or "").strip() or None,
        instructor=(data.get("instructor") or "").strip() or None,
        estado=estado,
        observaciones=(data.get("observaciones") or "").strip() or None,
    )
    db.session.add(encuentro)
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
    if "estado" in data:
        estado = (data["estado"] or "").strip().lower()
        if estado not in ESTADOS_ENCUENTRO:
            raise ValueError("Estado inválido")
        enc.estado = estado
    if "observaciones" in data:
        enc.observaciones = (data.get("observaciones") or "").strip() or None

    db.session.commit()
    return _encuentro_dict(enc)


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

    participantes: list[Participante] = []
    if enc.programa_id:
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
    return {
        "id": e.id,
        "titulo": e.titulo,
        "fecha": e.fecha.isoformat(),
        "hora_inicio": e.hora_inicio.isoformat() if e.hora_inicio else None,
        "hora_fin": e.hora_fin.isoformat() if e.hora_fin else None,
        "lugar": e.lugar,
        "link_virtual": e.link_virtual,
        "instructor": e.instructor,
        "estado": e.estado,
        "programa_id": e.programa_id,
        "curso_id": e.curso_id,
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
