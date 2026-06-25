from decimal import Decimal, InvalidOperation

from gos.extensions import db
from gos.modulos.capacitacion.models import Curso, Participante, Puesto
from gos.modulos.objetivos.models.catalogos import Sector

MODALIDADES = ("presencial", "virtual", "mixta")


def listar_cursos(empresa_id: int) -> list[dict]:
    items = (
        Curso.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(Curso.codigo)
        .all()
    )
    return [_curso_dict(c) for c in items]


def listar_puestos(empresa_id: int) -> list[dict]:
    items = (
        Puesto.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(Puesto.codigo)
        .all()
    )
    return [_puesto_dict(p) for p in items]


def listar_sectores(empresa_id: int) -> list[dict]:
    items = Sector.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Sector.codigo).all()
    return [{"id": s.id, "codigo": s.codigo, "nombre": s.nombre} for s in items]


def crear_curso(empresa_id: int, data: dict) -> dict:
    codigo = (data.get("codigo") or "").strip()
    nombre = (data.get("nombre") or "").strip()
    if not codigo or not nombre:
        raise ValueError("Código y nombre son obligatorios")
    if Curso.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe un curso con el código «{codigo}»")

    modalidad = (data.get("modalidad") or "").strip().lower() or None
    if modalidad and modalidad not in MODALIDADES:
        raise ValueError("Modalidad inválida (presencial, virtual o mixta)")

    horas = _parse_decimal(data.get("horas"))
    vigencia = _parse_int(data.get("vigencia_meses"))

    curso = Curso(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
        descripcion=(data.get("descripcion") or "").strip() or None,
        horas=horas,
        modalidad=modalidad,
        vigencia_meses=vigencia,
    )
    db.session.add(curso)
    db.session.commit()
    return _curso_dict(curso)


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

    legajo = (data.get("legajo") or "").strip() or None
    if legajo and Participante.query.filter_by(empresa_id=empresa_id, legajo=legajo).first():
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

    participante = Participante(
        empresa_id=empresa_id,
        nombre=nombre,
        legajo=legajo,
        email=email,
        sector_id=sector_id,
        puesto_id=puesto_id,
    )
    db.session.add(participante)
    db.session.commit()
    return _participante_dict(participante)


def _curso_dict(curso: Curso) -> dict:
    return {
        "id": curso.id,
        "codigo": curso.codigo,
        "nombre": curso.nombre,
        "descripcion": curso.descripcion,
        "horas": float(curso.horas) if curso.horas is not None else None,
        "modalidad": curso.modalidad,
        "vigencia_meses": curso.vigencia_meses,
    }


def _puesto_dict(puesto: Puesto) -> dict:
    return {
        "id": puesto.id,
        "codigo": puesto.codigo,
        "nombre": puesto.nombre,
        "descripcion": puesto.descripcion,
    }


def _participante_dict(p: Participante) -> dict:
    return {
        "id": p.id,
        "nombre": p.nombre,
        "legajo": p.legajo,
        "email": p.email,
        "sector_id": p.sector_id,
        "puesto_id": p.puesto_id,
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
