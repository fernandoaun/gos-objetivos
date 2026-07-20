from decimal import Decimal, InvalidOperation

from gos.extensions import db
from gos.modulos.capacitacion.models import Centro, Curso, EmpresaCapacitadora, Instructor, Participante, Puesto
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
    # Limpia del catálogo los puestos viejos sin personas (p. ej. renombres / reimport).
    desactivar_puestos_huerfanos(empresa_id, gracia_horas=1)
    items = (
        Puesto.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(Puesto.codigo)
        .all()
    )
    usados = _puestos_en_uso_ids(empresa_id)
    return [_puesto_dict(p, en_uso=p.id in usados) for p in items]


def desactivar_puestos_huerfanos(
    empresa_id: int, *, gracia_horas: float | None = None
) -> int:
    """Da de baja puestos activos sin ninguna persona activa asignada.

    Si `gracia_horas` está definido, no toca puestos creados dentro de esa ventana
    (así un alta rápida no desaparece antes de asignar personas).
    """
    from datetime import timedelta

    from gos.models.base import utcnow

    usados = _puestos_en_uso_ids(empresa_id)
    q = Puesto.query.filter_by(empresa_id=empresa_id, activo=True)
    if usados:
        q = q.filter(~Puesto.id.in_(usados))
    if gracia_horas is not None:
        corte = utcnow() - timedelta(hours=gracia_horas)
        # Sin created_at (datos viejos) se consideran huérfanos a limpiar.
        q = q.filter(db.or_(Puesto.created_at.is_(None), Puesto.created_at < corte))
    huerfanos = q.all()
    if not huerfanos:
        return 0

    from gos.modulos.capacitacion.models import ProgramaPuesto

    ids = [p.id for p in huerfanos]
    ProgramaPuesto.query.filter(ProgramaPuesto.puesto_id.in_(ids)).delete(
        synchronize_session=False
    )
    for puesto in huerfanos:
        puesto.activo = False
    db.session.commit()
    return len(huerfanos)


def _puestos_en_uso_ids(empresa_id: int) -> set[int]:
    rows = (
        db.session.query(Participante.puesto_id)
        .filter(
            Participante.empresa_id == empresa_id,
            Participante.activo.is_(True),
            Participante.puesto_id.isnot(None),
        )
        .distinct()
        .all()
    )
    return {row[0] for row in rows if row[0] is not None}


def listar_centros(empresa_id: int) -> list[dict]:
    items = (
        Centro.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(Centro.codigo)
        .all()
    )
    return [_centro_dict(c) for c in items]


def listar_participantes_por_puestos(empresa_id: int, puesto_ids: list[int]) -> list[dict]:
    """Participantes activos asignados a uno o más puestos (cronograma)."""
    if not puesto_ids:
        return []
    items = (
        Participante.query.filter_by(empresa_id=empresa_id, activo=True)
        .filter(Participante.puesto_id.in_(puesto_ids))
        .order_by(Participante.nombre)
        .all()
    )
    return [_participante_resumen_dict(p) for p in items]


def listar_sectores(empresa_id: int) -> list[dict]:
    items = Sector.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Sector.codigo).all()
    return [_sector_dict(s) for s in items]


def listar_instructores(empresa_id: int) -> list[dict]:
    items = (
        Instructor.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(Instructor.nombre)
        .all()
    )
    return [_instructor_dict(i) for i in items]


def crear_instructor(empresa_id: int, data: dict) -> dict:
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre del capacitador es obligatorio")
    if not codigo:
        base = "".join(ch for ch in nombre.upper() if ch.isalnum())[:12] or "CAP"
        codigo = base
        n = 1
        while Instructor.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
            codigo = f"{base}{n}"
            n += 1
    elif Instructor.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe un capacitador con el código «{codigo}»")

    instructor = Instructor(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        email=(data.get("email") or "").strip() or None,
        telefono=(data.get("telefono") or "").strip() or None,
        especialidad=(data.get("especialidad") or "").strip() or None,
    )
    db.session.add(instructor)
    db.session.commit()
    return _instructor_dict(instructor)


def listar_empresas_capacitadoras(empresa_id: int) -> list[dict]:
    items = (
        EmpresaCapacitadora.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(EmpresaCapacitadora.nombre)
        .all()
    )
    return [_empresa_capacitadora_dict(e) for e in items]


def crear_empresa_capacitadora(empresa_id: int, data: dict) -> dict:
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre de la empresa capacitadora es obligatorio")
    if not codigo:
        base = "".join(ch for ch in nombre.upper() if ch.isalnum())[:12] or "EXT"
        codigo = base
        n = 1
        while EmpresaCapacitadora.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
            codigo = f"{base}{n}"
            n += 1
    elif EmpresaCapacitadora.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe una empresa con el código «{codigo}»")

    empresa = EmpresaCapacitadora(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        contacto=(data.get("contacto") or "").strip() or None,
        telefono=(data.get("telefono") or "").strip() or None,
        email=(data.get("email") or "").strip() or None,
    )
    db.session.add(empresa)
    db.session.commit()
    return _empresa_capacitadora_dict(empresa)


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
    if "sector_id" in data:
        puesto.sector_id = _parse_sector_id(empresa_id, data)
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

    horas = _parse_decimal(data.get("horas") or data.get("duracion_horas"))
    tiene_vigencia = data.get("tiene_vigencia")
    if tiene_vigencia is False or str(tiene_vigencia).lower() in ("0", "false", "no"):
        vigencia = None
    else:
        vigencia = _parse_int(data.get("vigencia_meses") or data.get("meses_vigencia"))
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
        temas=(data.get("temas") or "").strip() or None,
        vigencia_meses=vigencia,
        requiere_evaluacion=requiere_eval,
        puntaje_minimo=puntaje if requiere_eval else None,
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
    curso.horas = _parse_decimal(data.get("horas") or data.get("duracion_horas"))
    curso.modalidad = modalidad
    if "temas" in data:
        curso.temas = (data.get("temas") or "").strip() or None
    tiene_vigencia = data.get("tiene_vigencia")
    if tiene_vigencia is False or str(tiene_vigencia).lower() in ("0", "false", "no"):
        curso.vigencia_meses = None
    else:
        curso.vigencia_meses = _parse_int(data.get("vigencia_meses") or data.get("meses_vigencia"))
    curso.requiere_evaluacion = bool(data.get("requiere_evaluacion"))
    curso.puntaje_minimo = (
        _parse_decimal(data.get("puntaje_minimo")) if curso.requiere_evaluacion else None
    )
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


def obtener_participante(empresa_id: int, participante_id: int) -> dict:
    participante = Participante.query.filter_by(
        id=participante_id, empresa_id=empresa_id, activo=True
    ).first()
    if not participante:
        raise ValueError("Participante no encontrado")
    data = _participante_dict(participante)
    data["sector_nombre"] = participante.sector.nombre if participante.sector else None
    data["puesto_nombre"] = participante.puesto.nombre if participante.puesto else None
    data["centro_nombre"] = participante.centro.nombre if participante.centro else None
    return data


def crear_puesto(empresa_id: int, data: dict) -> dict:
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    if Puesto.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe un puesto con el código «{codigo}»")

    sector_id = _parse_sector_id(empresa_id, data)
    puesto = Puesto(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        descripcion=(data.get("descripcion") or "").strip() or None,
        sector_id=sector_id,
    )
    db.session.add(puesto)
    db.session.commit()
    return _puesto_dict(puesto)


def crear_centro(empresa_id: int, data: dict) -> dict:
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    if Centro.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe un centro con el código «{codigo}»")

    centro = Centro(empresa_id=empresa_id, codigo=codigo, nombre=nombre)
    db.session.add(centro)
    db.session.commit()
    return _centro_dict(centro)


def actualizar_centro(empresa_id: int, centro_id: int, data: dict) -> dict:
    centro = _get_centro(empresa_id, centro_id)
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    dup = (
        Centro.query.filter_by(empresa_id=empresa_id, codigo=codigo)
        .filter(Centro.id != centro_id)
        .first()
    )
    if dup:
        raise ValueError(f"Ya existe un centro con el código «{codigo}»")

    centro.codigo = codigo
    centro.nombre = nombre
    db.session.commit()
    return _centro_dict(centro)


def _codigo_desde_texto(texto: str, fallback: str) -> str:
    base = "".join(ch for ch in texto.upper() if ch.isalnum())[:12] or fallback
    return base


def sector_id_desde_texto(
    empresa_id: int, texto: str | None, *, crear_si_falta: bool = True
) -> int | None:
    """Resuelve un sector por código o nombre; opcionalmente lo crea en catálogo."""
    nombre = (texto or "").strip()
    if not nombre:
        return None
    norm = nombre.lower()
    for sector in Sector.query.filter_by(empresa_id=empresa_id, activo=True).all():
        if sector.codigo.strip().lower() == norm or sector.nombre.strip().lower() == norm:
            return sector.id
    if not crear_si_falta:
        return None

    base = _codigo_desde_texto(nombre, "SEC")
    codigo = base
    n = 1
    while Sector.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        codigo = f"{base}{n}"
        n += 1

    sector = Sector(empresa_id=empresa_id, codigo=codigo, nombre=nombre)
    db.session.add(sector)
    db.session.flush()
    return sector.id


def puesto_id_desde_texto(
    empresa_id: int,
    texto: str | None,
    *,
    sector_id: int | None = None,
    crear_si_falta: bool = True,
) -> int | None:
    """Resuelve un puesto por código o nombre; opcionalmente lo crea en catálogo."""
    nombre = (texto or "").strip()
    if not nombre:
        return None
    norm = nombre.lower()
    for puesto in Puesto.query.filter_by(empresa_id=empresa_id, activo=True).all():
        if puesto.codigo.strip().lower() == norm or puesto.nombre.strip().lower() == norm:
            return puesto.id
    if not crear_si_falta:
        return None

    base = _codigo_desde_texto(nombre, "PST")
    codigo = base
    n = 1
    while Puesto.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        codigo = f"{base}{n}"
        n += 1

    puesto = Puesto(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        sector_id=sector_id,
    )
    db.session.add(puesto)
    db.session.flush()
    return puesto.id


def centro_id_desde_texto(empresa_id: int, texto: str | None) -> int | None:
    """Resuelve un centro por nombre; lo crea en catálogo si no existe."""
    nombre = (texto or "").strip()
    if not nombre:
        return None
    norm = nombre.lower()
    for centro in Centro.query.filter_by(empresa_id=empresa_id, activo=True).all():
        if centro.nombre.strip().lower() == norm:
            return centro.id

    base = "".join(ch for ch in nombre.upper() if ch.isalnum())[:12] or "CTR"
    codigo = base
    n = 1
    while Centro.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        codigo = f"{base}{n}"
        n += 1

    centro = Centro(empresa_id=empresa_id, codigo=codigo, nombre=nombre)
    db.session.add(centro)
    db.session.flush()
    return centro.id


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

    if puesto_id is not None and puesto_id != "":
        puesto_id = int(puesto_id)
        puesto = Puesto.query.filter_by(id=puesto_id, empresa_id=empresa_id, activo=True).first()
        if not puesto:
            raise ValueError("Puesto no válido")
        if sector_id is None and puesto.sector_id:
            sector_id = puesto.sector_id
    else:
        puesto_id = None

    centro_id = _parse_centro_id(empresa_id, data)
    if centro_id is None and data.get("centro"):
        centro_id = centro_id_desde_texto(empresa_id, data.get("centro"))

    email = (data.get("email") or "").strip() or None
    _validar_email_unico(empresa_id, email)
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
        centro_id=centro_id,
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
        puesto = Puesto.query.filter_by(id=puesto_id, empresa_id=empresa_id, activo=True).first()
        if not puesto:
            raise ValueError("Puesto no válido")
        if sector_id is None and puesto.sector_id:
            sector_id = puesto.sector_id
    else:
        puesto_id = None

    centro_id = _parse_centro_id(empresa_id, data)
    if centro_id is None and data.get("centro"):
        centro_id = centro_id_desde_texto(empresa_id, data.get("centro"))

    email = (data.get("email") or "").strip() or None
    _validar_email_unico(empresa_id, email, exclude_id=participante_id)

    participante.nombre = nombre
    participante.apellido = (data.get("apellido") or "").strip() or None
    participante.legajo = legajo
    if "dni" in data:
        participante.dni = (data.get("dni") or "").strip() or None
    participante.email = email
    if "telefono" in data:
        participante.telefono = (data.get("telefono") or "").strip() or None
    participante.centro_id = centro_id
    if "fecha_ingreso" in data:
        participante.fecha_ingreso = _parse_date(data.get("fecha_ingreso"))
    participante.observaciones = (data.get("observaciones") or "").strip() or None
    if "activo" in data:
        participante.activo = bool(data["activo"])
    participante.sector_id = sector_id
    puesto_anterior = participante.puesto_id
    participante.puesto_id = puesto_id
    db.session.commit()

    # La matriz recalcula programas aplicables según el puesto actual (lectura dinámica)
    if puesto_anterior != puesto_id:
        from gos.modulos.capacitacion.services.acreditacion_service import refrescar_vigencias

        refrescar_vigencias(empresa_id)

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


def _get_centro(empresa_id: int, centro_id: int) -> Centro:
    centro = Centro.query.filter_by(id=centro_id, empresa_id=empresa_id, activo=True).first()
    if not centro:
        raise ValueError("Centro no encontrado")
    return centro


def _parse_centro_id(empresa_id: int, data: dict) -> int | None:
    centro_id = data.get("centro_id")
    if centro_id is not None and centro_id != "":
        centro_id = int(centro_id)
        if not Centro.query.filter_by(id=centro_id, empresa_id=empresa_id, activo=True).first():
            raise ValueError("Centro no válido")
        return centro_id
    return None


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
        "duracion_horas": float(curso.horas) if curso.horas is not None else None,
        "modalidad": curso.modalidad,
        "temas": curso.temas,
        "tiene_vigencia": curso.tiene_vigencia,
        "vigencia_meses": curso.vigencia_meses,
        "meses_vigencia": curso.vigencia_meses,
        "requiere_evaluacion": curso.requiere_evaluacion,
        "puntaje_minimo": float(curso.puntaje_minimo) if curso.puntaje_minimo is not None else None,
        "instructor_id": curso.instructor_id,
        "activo": curso.activo,
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
        "centro_id": p.centro_id,
        "centro_nombre": p.centro.nombre if p.centro else None,
        "fecha_ingreso": p.fecha_ingreso.isoformat() if p.fecha_ingreso else None,
        "observaciones": p.observaciones,
        "tiene_foto": bool(p.foto_path),
        "activo": p.activo,
        "sector_id": p.sector_id,
        "puesto_id": p.puesto_id,
    }


def _participante_resumen_dict(p: Participante) -> dict:
    return {
        "id": p.id,
        "nombre": p.nombre_completo,
        "legajo": p.legajo,
        "dni": p.dni,
        "tiene_foto": bool(p.foto_path),
        "sector_id": p.sector_id,
        "puesto_id": p.puesto_id,
        "puesto_nombre": p.puesto.nombre if p.puesto else None,
        "centro_id": p.centro_id,
        "centro_nombre": p.centro.nombre if p.centro else None,
        "activo": p.activo,
    }


def _puesto_dict(puesto: Puesto, *, en_uso: bool | None = None) -> dict:
    if en_uso is None:
        en_uso = (
            Participante.query.filter_by(
                empresa_id=puesto.empresa_id,
                puesto_id=puesto.id,
                activo=True,
            ).count()
            > 0
        )
    return {
        "id": puesto.id,
        "codigo": puesto.codigo,
        "nombre": puesto.nombre,
        "descripcion": puesto.descripcion,
        "sector_id": puesto.sector_id,
        "sector_nombre": puesto.sector.nombre if puesto.sector else None,
        "en_uso": bool(en_uso),
    }


def _centro_dict(centro: Centro) -> dict:
    return {"id": centro.id, "codigo": centro.codigo, "nombre": centro.nombre}


def _parse_sector_id(empresa_id: int, data: dict) -> int | None:
    sector_id = data.get("sector_id")
    if sector_id is not None and sector_id != "":
        sector_id = int(sector_id)
        if not Sector.query.filter_by(id=sector_id, empresa_id=empresa_id, activo=True).first():
            raise ValueError("Sector no válido")
        return sector_id
    return None


def _validar_email_unico(
    empresa_id: int, email: str | None, *, exclude_id: int | None = None
) -> None:
    if not email:
        return
    q = Participante.query.filter_by(empresa_id=empresa_id, email=email)
    if exclude_id:
        q = q.filter(Participante.id != exclude_id)
    if q.first():
        raise ValueError(f"Ya existe una persona con el email «{email}»")


def _instructor_dict(instructor: Instructor) -> dict:
    return {
        "id": instructor.id,
        "codigo": instructor.codigo,
        "nombre": instructor.nombre,
        "email": instructor.email,
        "telefono": instructor.telefono,
        "especialidad": instructor.especialidad,
    }


def _empresa_capacitadora_dict(empresa: EmpresaCapacitadora) -> dict:
    return {
        "id": empresa.id,
        "codigo": empresa.codigo,
        "nombre": empresa.nombre,
        "contacto": empresa.contacto,
        "telefono": empresa.telefono,
        "email": empresa.email,
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
