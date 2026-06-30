from decimal import Decimal, InvalidOperation

from gos.extensions import db
from gos.modulos.capacitacion.models import Curso, Participante, Puesto
from gos.modulos.capacitacion.services.taxonomia_service import (
    arbol_taxonomia,
    etiqueta_taxonomia,
    listas_taxonomia_planas,
    tipo_capacitacion_legacy,
    validar_clasificacion,
)
from gos.modulos.objetivos.models.catalogos import Sector


def obtener_taxonomia_cursos(empresa_id: int) -> dict:
    return {
        "cascada": arbol_taxonomia(empresa_id),
        "listas": listas_taxonomia_planas(empresa_id),
    }


def listar_cursos(empresa_id: int) -> list[dict]:
    items = (
        Curso.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(Curso.codigo)
        .all()
    )
    return [_curso_dict(c, empresa_id) for c in items]


def listar_puestos(empresa_id: int) -> list[dict]:
    items = (
        Puesto.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(Puesto.codigo)
        .all()
    )
    return [_puesto_dict(p) for p in items]


def listar_sectores(empresa_id: int) -> list[dict]:
    items = Sector.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Sector.codigo).all()
    return [_sector_dict(s) for s in items]


def crear_sector(empresa_id: int, data: dict) -> dict:
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    if Sector.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe un sector con el código «{codigo}»")

    sector = Sector(empresa_id=empresa_id, codigo=codigo, nombre=nombre)
    db.session.add(sector)
    db.session.commit()
    return _sector_dict(sector)


def actualizar_sector(empresa_id: int, sector_id: int, data: dict) -> dict:
    sector = _get_sector(empresa_id, sector_id)
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    dup = (
        Sector.query.filter_by(empresa_id=empresa_id, codigo=codigo)
        .filter(Sector.id != sector_id)
        .first()
    )
    if dup:
        raise ValueError(f"Ya existe un sector con el código «{codigo}»")

    sector.codigo = codigo
    sector.nombre = nombre
    db.session.commit()
    return _sector_dict(sector)


def actualizar_puesto(empresa_id: int, puesto_id: int, data: dict) -> dict:
    puesto = _get_puesto(empresa_id, puesto_id)
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    dup = (
        Puesto.query.filter_by(empresa_id=empresa_id, codigo=codigo)
        .filter(Puesto.id != puesto_id)
        .first()
    )
    if dup:
        raise ValueError(f"Ya existe un puesto con el código «{codigo}»")

    puesto.codigo = codigo
    puesto.nombre = nombre
    descripcion = (data.get("descripcion") or "").strip()
    puesto.descripcion = descripcion or None
    db.session.commit()
    return _puesto_dict(puesto)


def crear_curso(empresa_id: int, data: dict) -> dict:
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    if Curso.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe un curso con el código «{codigo}»")

    modalidad = (data.get("modalidad") or "").strip().lower() or None
    categoria, tipo, origen, modalidad = validar_clasificacion(
        empresa_id,
        data.get("categoria"),
        data.get("tipo"),
        data.get("origen"),
        modalidad,
    )

    horas = _parse_decimal(data.get("horas"))
    vigencia = _parse_int(data.get("vigencia_meses"))
    puntaje = _parse_decimal(data.get("puntaje_minimo"))
    requiere_eval = bool(data.get("requiere_evaluacion"))
    instructor_id = data.get("instructor_id")
    if instructor_id:
        instructor_id = int(instructor_id)

    curso = Curso(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        descripcion=(data.get("descripcion") or "").strip() or None,
        categoria=categoria,
        tipo=tipo,
        origen=origen,
        tipo_capacitacion=tipo_capacitacion_legacy(categoria, tipo),
        horas=horas,
        modalidad=modalidad,
        vigencia_meses=vigencia,
        requiere_evaluacion=requiere_eval,
        puntaje_minimo=puntaje,
        instructor_id=instructor_id,
    )
    db.session.add(curso)
    db.session.commit()
    return _curso_dict(curso, empresa_id)


def actualizar_curso(empresa_id: int, curso_id: int, data: dict) -> dict:
    curso = Curso.query.filter_by(id=curso_id, empresa_id=empresa_id, activo=True).first()
    if not curso:
        raise ValueError("Curso no encontrado")

    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    dup = (
        Curso.query.filter_by(empresa_id=empresa_id, codigo=codigo)
        .filter(Curso.id != curso_id)
        .first()
    )
    if dup:
        raise ValueError(f"Ya existe un curso con el código «{codigo}»")

    modalidad = (data.get("modalidad") or "").strip().lower() or None
    categoria, tipo, origen, modalidad = validar_clasificacion(
        empresa_id,
        data.get("categoria"),
        data.get("tipo"),
        data.get("origen"),
        modalidad,
    )

    curso.codigo = codigo
    curso.nombre = nombre
    curso.descripcion = (data.get("descripcion") or "").strip() or None
    curso.categoria = categoria
    curso.tipo = tipo
    curso.origen = origen
    curso.tipo_capacitacion = tipo_capacitacion_legacy(categoria, tipo)
    curso.horas = _parse_decimal(data.get("horas"))
    curso.modalidad = modalidad
    curso.vigencia_meses = _parse_int(data.get("vigencia_meses"))
    curso.requiere_evaluacion = bool(data.get("requiere_evaluacion"))
    curso.puntaje_minimo = _parse_decimal(data.get("puntaje_minimo"))
    instructor_id = data.get("instructor_id")
    curso.instructor_id = int(instructor_id) if instructor_id else None
    db.session.commit()
    return _curso_dict(curso, empresa_id)


def baja_curso(empresa_id: int, curso_id: int) -> dict:
    curso = Curso.query.filter_by(id=curso_id, empresa_id=empresa_id, activo=True).first()
    if not curso:
        raise ValueError("Curso no encontrado")
    curso.activo = False
    db.session.commit()
    return {"id": curso.id, "activo": False}


def baja_participante(empresa_id: int, participante_id: int) -> dict:
    participante = Participante.query.filter_by(
        id=participante_id, empresa_id=empresa_id, activo=True
    ).first()
    if not participante:
        raise ValueError("Participante no encontrado")
    participante.activo = False
    db.session.commit()
    return {"id": participante.id, "activo": False}


def crear_puesto(empresa_id: int, data: dict) -> dict:
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    if Puesto.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe un puesto con el código «{codigo}»")

    puesto = Puesto(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        descripcion=(data.get("descripcion") or "").strip() or None,
    )
    db.session.add(puesto)
    db.session.commit()
    return _puesto_dict(puesto)


def crear_participante(empresa_id: int, data: dict) -> dict:
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre es obligatorio")

    legajo = (data.get("legajo") or "").strip()
    if not legajo:
        raise ValueError("El legajo es obligatorio")
    if Participante.query.filter_by(empresa_id=empresa_id, legajo=legajo).first():
        raise ValueError(f"Ya existe una persona con el legajo «{legajo}»")

    sector_id = data.get("sector_id")
    puesto_id = data.get("puesto_id")
    if sector_id is not None:
        sector_id = int(sector_id)
        if not Sector.query.filter_by(id=sector_id, empresa_id=empresa_id, activo=True).first():
            raise ValueError("Sector no válido")
    else:
        sector_id = None

    if puesto_id is not None:
        puesto_id = int(puesto_id)
        if not Puesto.query.filter_by(id=puesto_id, empresa_id=empresa_id, activo=True).first():
            raise ValueError("Puesto no válido")
    else:
        puesto_id = None

    email = (data.get("email") or "").strip() or None
    apellido = (data.get("apellido") or "").strip() or None
    dni = (data.get("dni") or "").strip() or None
    telefono = (data.get("telefono") or "").strip() or None
    fecha_ingreso = _parse_date(data.get("fecha_ingreso"))
    observaciones = (data.get("observaciones") or "").strip() or None

    participante = Participante(
        empresa_id=empresa_id,
        nombre=nombre,
        apellido=apellido,
        legajo=legajo,
        dni=dni,
        email=email,
        telefono=telefono,
        fecha_ingreso=fecha_ingreso,
        observaciones=observaciones,
        sector_id=sector_id,
        puesto_id=puesto_id,
    )
    db.session.add(participante)
    db.session.commit()
    return _participante_dict(participante)


def actualizar_participante(empresa_id: int, participante_id: int, data: dict) -> dict:
    participante = Participante.query.filter_by(
        id=participante_id, empresa_id=empresa_id, activo=True
    ).first()
    if not participante:
        raise ValueError("Participante no encontrado")

    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre es obligatorio")

    legajo = (data.get("legajo") or "").strip()
    if not legajo:
        raise ValueError("El legajo es obligatorio")
    dup = (
        Participante.query.filter_by(empresa_id=empresa_id, legajo=legajo)
        .filter(Participante.id != participante_id)
        .first()
    )
    if dup:
        raise ValueError(f"Ya existe una persona con el legajo «{legajo}»")

    sector_id = data.get("sector_id")
    puesto_id = data.get("puesto_id")
    if sector_id is not None and sector_id != "":
        sector_id = int(sector_id)
        if not Sector.query.filter_by(id=sector_id, empresa_id=empresa_id, activo=True).first():
            raise ValueError("Sector no válido")
    else:
        sector_id = None

    if puesto_id is not None and puesto_id != "":
        puesto_id = int(puesto_id)
        if not Puesto.query.filter_by(id=puesto_id, empresa_id=empresa_id, activo=True).first():
            raise ValueError("Puesto no válido")
    else:
        puesto_id = None

    participante.nombre = nombre
    participante.apellido = (data.get("apellido") or "").strip() or None
    participante.legajo = legajo
    participante.dni = (data.get("dni") or "").strip() or None
    participante.email = (data.get("email") or "").strip() or None
    participante.telefono = (data.get("telefono") or "").strip() or None
    participante.fecha_ingreso = _parse_date(data.get("fecha_ingreso"))
    participante.observaciones = (data.get("observaciones") or "").strip() or None
    if "activo" in data:
        participante.activo = bool(data["activo"])
    participante.sector_id = sector_id
    participante.puesto_id = puesto_id
    db.session.commit()
    return _participante_dict(participante)


def _get_sector(empresa_id: int, sector_id: int) -> Sector:
    sector = Sector.query.filter_by(id=sector_id, empresa_id=empresa_id, activo=True).first()
    if not sector:
        raise ValueError("Sector no encontrado")
    return sector


def _get_puesto(empresa_id: int, puesto_id: int) -> Puesto:
    puesto = Puesto.query.filter_by(id=puesto_id, empresa_id=empresa_id, activo=True).first()
    if not puesto:
        raise ValueError("Puesto no encontrado")
    return puesto


def _sector_dict(sector: Sector) -> dict:
    return {"id": sector.id, "codigo": sector.codigo, "nombre": sector.nombre}


def _curso_dict(curso: Curso, empresa_id: int) -> dict:
    return {
        "id": curso.id,
        "codigo": curso.codigo,
        "nombre": curso.nombre,
        "descripcion": curso.descripcion,
        "categoria": curso.categoria,
        "tipo": curso.tipo,
        "origen": curso.origen,
        "categoria_label": etiqueta_taxonomia(empresa_id, "categoria", curso.categoria),
        "tipo_label": etiqueta_taxonomia(empresa_id, "tipo", curso.tipo),
        "origen_label": etiqueta_taxonomia(empresa_id, "origen", curso.origen),
        "modalidad_label": etiqueta_taxonomia(empresa_id, "modalidad", curso.modalidad),
        "tipo_capacitacion": curso.tipo_capacitacion,
        "horas": float(curso.horas) if curso.horas is not None else None,
        "modalidad": curso.modalidad,
        "vigencia_meses": curso.vigencia_meses,
        "requiere_evaluacion": curso.requiere_evaluacion,
        "puntaje_minimo": float(curso.puntaje_minimo) if curso.puntaje_minimo is not None else None,
        "instructor_id": curso.instructor_id,
    }


def _participante_dict(p: Participante) -> dict:
    return {
        "id": p.id,
        "nombre": p.nombre,
        "apellido": p.apellido,
        "nombre_completo": p.nombre_completo,
        "legajo": p.legajo,
        "dni": p.dni,
        "email": p.email,
        "telefono": p.telefono,
        "fecha_ingreso": p.fecha_ingreso.isoformat() if p.fecha_ingreso else None,
        "observaciones": p.observaciones,
        "tiene_foto": bool(p.foto_path),
        "activo": p.activo,
        "sector_id": p.sector_id,
        "puesto_id": p.puesto_id,
    }


def _puesto_dict(puesto: Puesto) -> dict:
    return {
        "id": puesto.id,
        "codigo": puesto.codigo,
        "nombre": puesto.nombre,
        "descripcion": puesto.descripcion,
    }


def _parse_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        raise ValueError("Horas inválidas") from None


def _parse_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError("Vigencia inválida") from None


def _parse_date(value):
    if value is None or value == "":
        return None
    from datetime import date as dt_date

    if isinstance(value, dt_date):
        return value
    return dt_date.fromisoformat(str(value))
