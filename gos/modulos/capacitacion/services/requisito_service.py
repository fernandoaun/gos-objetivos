from gos.extensions import db
from gos.modulos.capacitacion.models import Curso, Participante, Puesto, RequisitoFormacion
from gos.modulos.objetivos.models.catalogos import Sector


def listar_requisitos(
    empresa_id: int,
    *,
    puesto_id: int | None = None,
    sector_id: int | None = None,
    participante_id: int | None = None,
) -> list[dict]:
    q = RequisitoFormacion.query.filter_by(empresa_id=empresa_id)
    if puesto_id:
        q = q.filter_by(puesto_id=puesto_id)
    if sector_id:
        q = q.filter_by(sector_id=sector_id)
    if participante_id:
        q = q.filter_by(participante_id=participante_id)
    items = q.order_by(RequisitoFormacion.id).all()
    return [_requisito_dict(r) for r in items]


def crear_requisito(empresa_id: int, data: dict) -> dict:
    puesto_id = data.get("puesto_id") or None
    sector_id = data.get("sector_id") or None
    participante_id = data.get("participante_id") or None
    curso_id = data.get("curso_id")
    certificacion_tipo_id = data.get("certificacion_tipo_id") or None

    if not curso_id and not certificacion_tipo_id:
        raise ValueError("Debe indicar un curso o tipo de certificación")
    if not any([puesto_id, sector_id, participante_id]):
        raise ValueError("Debe indicar puesto, sector o persona")

    targets = sum(1 for x in (puesto_id, sector_id, participante_id) if x)
    if targets > 1:
        raise ValueError("Indique solo uno: puesto, sector o persona")

    if puesto_id and not Puesto.query.filter_by(id=puesto_id, empresa_id=empresa_id, activo=True).first():
        raise ValueError("Puesto no válido")
    if sector_id and not Sector.query.filter_by(id=sector_id, empresa_id=empresa_id, activo=True).first():
        raise ValueError("Sector no válido")
    if participante_id and not Participante.query.filter_by(
        id=participante_id, empresa_id=empresa_id, activo=True
    ).first():
        raise ValueError("Persona no válida")
    if curso_id and not Curso.query.filter_by(id=curso_id, empresa_id=empresa_id, activo=True).first():
        raise ValueError("Curso no válido")

    dup_q = RequisitoFormacion.query.filter_by(empresa_id=empresa_id)
    if puesto_id:
        dup_q = dup_q.filter_by(puesto_id=puesto_id)
    if sector_id:
        dup_q = dup_q.filter_by(sector_id=sector_id)
    if participante_id:
        dup_q = dup_q.filter_by(participante_id=participante_id)
    if curso_id:
        dup_q = dup_q.filter_by(curso_id=curso_id)
    if certificacion_tipo_id:
        dup_q = dup_q.filter_by(certificacion_tipo_id=certificacion_tipo_id)
    if dup_q.first():
        raise ValueError("Ya existe ese requisito para el destino indicado")

    req = RequisitoFormacion(
        empresa_id=empresa_id,
        puesto_id=puesto_id,
        sector_id=sector_id,
        participante_id=participante_id,
        curso_id=curso_id or None,
        certificacion_tipo_id=certificacion_tipo_id,
        obligatorio=bool(data.get("obligatorio", True)),
        observaciones=(data.get("observaciones") or "").strip() or None,
    )
    db.session.add(req)
    db.session.commit()
    return _requisito_dict(req)


def eliminar_requisito(empresa_id: int, requisito_id: int) -> None:
    req = RequisitoFormacion.query.filter_by(id=requisito_id, empresa_id=empresa_id).first()
    if not req:
        raise ValueError("Requisito no encontrado")
    db.session.delete(req)
    db.session.commit()


def _requisito_dict(r: RequisitoFormacion) -> dict:
    curso = r.curso
    puesto = r.puesto
    sector = r.sector
    participante = r.participante
    return {
        "id": r.id,
        "puesto_id": r.puesto_id,
        "puesto_nombre": puesto.nombre if puesto else None,
        "sector_id": r.sector_id,
        "sector_nombre": sector.nombre if sector else None,
        "participante_id": r.participante_id,
        "participante_nombre": participante.nombre_completo if participante else None,
        "curso_id": r.curso_id,
        "curso_codigo": curso.codigo if curso else None,
        "curso_nombre": curso.nombre if curso else None,
        "certificacion_tipo_id": r.certificacion_tipo_id,
        "obligatorio": r.obligatorio,
        "observaciones": r.observaciones,
    }
