"""Servicios del dashboard O&M (apertura de módulos)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from gos.extensions import db
from gos.modulos.om.models import OmAuditLog, OmItem, OmModule, OmPersonnel, OmPhone
from gos.models.usuario import Usuario

KIND_TO_FIELD = {"unit": "units", "tool": "tools", "supply": "supplies"}
FIELD_TO_KIND = {"units": "unit", "tools": "tool", "supplies": "supply"}


class OmValidationError(Exception):
    def __init__(self, message: str, field_errors: list | None = None):
        super().__init__(message)
        self.message = message
        self.field_errors = field_errors or []


class OmConflictError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
        self.code = "conflict"


class OmNotFoundError(Exception):
    def __init__(self, message: str = "Módulo no encontrado"):
        super().__init__(message)
        self.message = message


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.isoformat() + ("Z" if dt.tzinfo is None else "")


def _validate(data: dict) -> None:
    field_errors = []
    if not (data.get("code") or "").strip():
        field_errors.append(
            {"field": "code", "code": "required", "message": "El codigo es obligatorio"}
        )
    if not (data.get("name") or "").strip():
        field_errors.append(
            {"field": "name", "code": "required", "message": "El nombre es obligatorio"}
        )
    status = data.get("status")
    if status and status not in ("active", "inactive"):
        field_errors.append(
            {"field": "status", "code": "invalid", "message": "Estado invalido"}
        )
    if field_errors:
        raise OmValidationError("Datos de modulo invalidos", field_errors)


def _to_api_shape(row: OmModule) -> dict:
    units, tools, supplies = [], [], []
    for item in row.items or []:
        field = KIND_TO_FIELD.get(item.kind)
        if field == "units":
            units.append(
                {
                    "unidadId": item.unidad_id,
                    "value": item.value,
                }
            )
        elif field == "tools":
            tools.append(item.value)
        elif field == "supplies":
            supplies.append(item.value)

    personnel = []
    for p in row.personnel or []:
        personnel.append(
            {
                "participanteId": p.participante_id,
                "name": p.name,
                "role": p.role,
                "phones": [{"type": ph.type, "number": ph.number} for ph in (p.phones or [])],
            }
        )

    return {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "status": row.status,
        "schedule": row.schedule,
        "guard": row.guard,
        "location": row.location,
        "description": row.description,
        "personnel": personnel,
        "units": units,
        "tools": tools,
        "supplies": supplies,
        "createdAt": _iso(row.created_at),
        "updatedAt": _iso(row.updated_at),
    }


def _module_query():
    return (
        select(OmModule)
        .where(OmModule.deleted_at.is_(None))
        .options(
            selectinload(OmModule.personnel).selectinload(OmPersonnel.phones),
            selectinload(OmModule.items),
        )
        .order_by(OmModule.code)
    )


def list_modules(*, include_inactive: bool = True) -> list[dict]:
    q = _module_query()
    if not include_inactive:
        q = q.where(OmModule.status == "active")
    rows = db.session.scalars(q).unique().all()
    return [_to_api_shape(r) for r in rows]


def get_module_or_404(module_id: int) -> OmModule:
    row = db.session.scalars(
        _module_query().where(OmModule.id == module_id)
    ).unique().first()
    if not row:
        raise OmNotFoundError()
    return row


def _normalize_unit_entry(raw) -> tuple[str, int | None]:
    """Acepta string legacy o {value, unidadId}."""
    if isinstance(raw, dict):
        value = (raw.get("value") or raw.get("nombre") or "").strip()
        unidad_id = raw.get("unidadId") or raw.get("unidad_id") or raw.get("id")
        try:
            unidad_id = int(unidad_id) if unidad_id is not None else None
        except (TypeError, ValueError):
            unidad_id = None
        return value, unidad_id
    return str(raw or "").strip(), None


def _insert_relations(module: OmModule, data: dict) -> None:
    for i, person in enumerate(data.get("personnel") or []):
        participante_id = person.get("participanteId") or person.get("participante_id")
        try:
            participante_id = int(participante_id) if participante_id is not None else None
        except (TypeError, ValueError):
            participante_id = None
        personnel = OmPersonnel(
            module=module,
            participante_id=participante_id,
            name=person.get("name") or "",
            role=person.get("role") or None,
            sort_order=i,
        )
        db.session.add(personnel)
        db.session.flush()
        for phone in person.get("phones") or []:
            number = (phone.get("number") or "").strip()
            if not number:
                continue
            db.session.add(
                OmPhone(
                    personnel=personnel,
                    type=phone.get("type") or "Personal",
                    number=number,
                )
            )

    for field, kind in FIELD_TO_KIND.items():
        for i, raw in enumerate(data.get(field) or []):
            if kind == "unit":
                value, unidad_id = _normalize_unit_entry(raw)
                if not value:
                    continue
                db.session.add(
                    OmItem(
                        module=module,
                        kind=kind,
                        value=value,
                        unidad_id=unidad_id,
                        sort_order=i,
                    )
                )
            else:
                value = str(raw or "").strip()
                if not value:
                    continue
                db.session.add(
                    OmItem(module=module, kind=kind, value=value, sort_order=i)
                )


def catalog_personal(empresa_id: int, q: str | None = None) -> list[dict]:
    """Personas activas de Capacitación para asignar en O&M."""
    from gos.modulos.capacitacion.models.participante import Participante

    query = Participante.query.filter_by(empresa_id=empresa_id, activo=True)
    rows = query.order_by(Participante.apellido, Participante.nombre).all()
    needle = (q or "").strip().lower()
    items = []
    for p in rows:
        nombre = p.nombre_completo
        if needle and needle not in nombre.lower() and needle not in (p.legajo or "").lower():
            continue
        phones = []
        if p.telefono:
            phones.append({"type": "Personal", "number": p.telefono})
        items.append(
            {
                "id": p.id,
                "nombre": nombre,
                "legajo": p.legajo,
                "puesto": p.puesto.nombre if p.puesto else None,
                "telefono": p.telefono,
                "phones": phones,
            }
        )
    return items


def catalog_unidades() -> list[dict]:
    """Unidades activas de Mantenimiento para asignar en O&M."""
    from gos.modulos.mantenimiento.services import get_meta

    meta = get_meta(db.session)
    return [
        {
            "id": u["id"],
            "codigo": u["codigo"],
            "nombre": u["nombre"],
            "label": f'{u["codigo"]} — {u["nombre"]}',
        }
        for u in (meta.get("unidades") or [])
    ]


def _audit(
    *,
    user_id: int | None,
    action: str,
    entity: str,
    entity_id: str,
    before=None,
    after=None,
) -> None:
    db.session.add(
        OmAuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            before=before,
            after=after,
        )
    )


def create_module(data: dict, user_id: int | None) -> dict:
    _validate(data)
    code = data["code"].strip()
    existing = db.session.scalar(select(OmModule).where(OmModule.code == code))
    if existing:
        raise OmConflictError(f"Ya existe un modulo con el codigo {code}")

    module = OmModule(
        code=code,
        name=data["name"].strip(),
        status=data.get("status") or "active",
        schedule=data.get("schedule") or None,
        guard=data.get("guard") or None,
        location=data.get("location") or None,
        description=data.get("description") or None,
        created_by=user_id,
    )
    db.session.add(module)
    db.session.flush()
    _insert_relations(module, data)
    _audit(
        user_id=user_id,
        action="create",
        entity="module",
        entity_id=str(module.id),
        after=data,
    )
    db.session.commit()
    return _to_api_shape(get_module_or_404(module.id))


def update_module(module_id: int, data: dict, user_id: int | None) -> dict:
    _validate(data)
    module = get_module_or_404(module_id)
    before = _to_api_shape(module)
    code = data["code"].strip()

    if code != module.code:
        clash = db.session.scalar(
            select(OmModule).where(OmModule.code == code, OmModule.id != module_id)
        )
        if clash:
            raise OmConflictError(f"Ya existe un modulo con el codigo {code}")

    module.code = code
    module.name = data["name"].strip()
    module.status = data.get("status") or "active"
    module.schedule = data.get("schedule") or None
    module.guard = data.get("guard") or None
    module.location = data.get("location") or None
    module.description = data.get("description") or None
    module.updated_at = datetime.utcnow()
    module.updated_by = user_id

    # Reemplazar relaciones (mismo comportamiento que el backend Node)
    for person in list(module.personnel):
        db.session.delete(person)
    for item in list(module.items):
        db.session.delete(item)
    db.session.flush()
    _insert_relations(module, data)

    _audit(
        user_id=user_id,
        action="update",
        entity="module",
        entity_id=str(module.id),
        before=before,
        after=data,
    )
    db.session.commit()
    return _to_api_shape(get_module_or_404(module.id))


def soft_delete_module(module_id: int, user_id: int | None) -> None:
    module = get_module_or_404(module_id)
    before = _to_api_shape(module)
    module.deleted_at = datetime.utcnow()
    module.updated_by = user_id
    module.updated_at = datetime.utcnow()
    _audit(
        user_id=user_id,
        action="delete",
        entity="module",
        entity_id=str(module.id),
        before=before,
    )
    db.session.commit()


def list_audit(*, limit: int = 50, offset: int = 0) -> dict:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    total = db.session.scalar(select(func.count()).select_from(OmAuditLog)) or 0
    rows = db.session.execute(
        select(OmAuditLog, Usuario.email, Usuario.nombre)
        .outerjoin(Usuario, Usuario.id == OmAuditLog.user_id)
        .order_by(OmAuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    items = []
    for audit, email, nombre in rows:
        items.append(
            {
                "id": audit.id,
                "action": audit.action,
                "entity": audit.entity,
                "entity_id": audit.entity_id,
                "before": audit.before,
                "after": audit.after,
                "created_at": _iso(audit.created_at),
                "username": email or nombre or None,
            }
        )
    return {"items": items, "total": total}


def import_modules_payload(modules: list[dict], user_id: int | None = None) -> dict:
    """Importa módulos desde un array JSON. Idempotente por code."""
    created = 0
    skipped = 0
    errors: list[dict] = []
    for legacy in modules:
        try:
            create_module(
                {
                    "code": legacy.get("code"),
                    "name": legacy.get("name"),
                    "status": legacy.get("status"),
                    "schedule": legacy.get("schedule"),
                    "guard": legacy.get("guard"),
                    "location": legacy.get("location"),
                    "description": legacy.get("description"),
                    "personnel": legacy.get("personnel") or [],
                    "units": legacy.get("units") or [],
                    "tools": legacy.get("tools") or [],
                    "supplies": legacy.get("supplies") or [],
                },
                user_id,
            )
            created += 1
        except OmConflictError:
            skipped += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"code": legacy.get("code"), "message": str(exc)})
            db.session.rollback()
    return {"created": created, "skipped": skipped, "errors": errors}
