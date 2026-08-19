from __future__ import annotations

from gos.extensions import db
from gos.modulos.capacitacion.models import ClienteCapacitacion, Participante, ParticipanteCliente


def _codigo_desde_nombre(empresa_id: int, nombre: str) -> str:
    base = "".join(ch for ch in nombre.upper() if ch.isalnum())[:12] or "CLI"
    codigo = base
    n = 1
    while ClienteCapacitacion.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        codigo = f"{base}{n}"
        n += 1
    return codigo


def _cliente_ids_de(participante: Participante) -> list[int]:
    return [
        v.cliente_id
        for v in participante.clientes.order_by(ParticipanteCliente.cliente_id).all()
    ]


def cliente_dict(cliente: ClienteCapacitacion, *, personas_count: int | None = None) -> dict:
    if personas_count is None:
        personas_count = cliente.asignaciones.count()
    return {
        "id": cliente.id,
        "codigo": cliente.codigo,
        "nombre": cliente.nombre,
        "tiene_logo": bool(cliente.logo_path),
        "personas_count": personas_count,
        "activo": cliente.activo,
    }


def listar_clientes(empresa_id: int, *, incluir_inactivos: bool = False) -> list[dict]:
    q = ClienteCapacitacion.query.filter_by(empresa_id=empresa_id)
    if not incluir_inactivos:
        q = q.filter_by(activo=True)
    items = q.order_by(ClienteCapacitacion.nombre).all()
    return [cliente_dict(c) for c in items]


def obtener_cliente(empresa_id: int, cliente_id: int) -> ClienteCapacitacion:
    cliente = ClienteCapacitacion.query.filter_by(id=cliente_id, empresa_id=empresa_id).first()
    if not cliente or not cliente.activo:
        raise ValueError("Cliente no encontrado")
    return cliente


def crear_cliente(empresa_id: int, data: dict) -> dict:
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre del cliente es obligatorio")
    codigo = (data.get("codigo") or "").strip()
    if not codigo:
        codigo = _codigo_desde_nombre(empresa_id, nombre)
    elif ClienteCapacitacion.query.filter_by(empresa_id=empresa_id, codigo=codigo).first():
        raise ValueError(f"Ya existe un cliente con el código «{codigo}»")

    dup = (
        ClienteCapacitacion.query.filter_by(empresa_id=empresa_id, activo=True)
        .filter(db.func.lower(ClienteCapacitacion.nombre) == nombre.lower())
        .first()
    )
    if dup:
        raise ValueError(f"Ya existe un cliente con el nombre «{nombre}»")

    cliente = ClienteCapacitacion(
        empresa_id=empresa_id,
        codigo=codigo,
        nombre=nombre,
    )
    db.session.add(cliente)
    db.session.commit()
    return cliente_dict(cliente)


def actualizar_cliente(empresa_id: int, cliente_id: int, data: dict) -> dict:
    cliente = obtener_cliente(empresa_id, cliente_id)
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre del cliente es obligatorio")
    codigo = (data.get("codigo") or cliente.codigo or "").strip()
    if not codigo:
        raise ValueError("El código es obligatorio")

    dup_cod = (
        ClienteCapacitacion.query.filter_by(empresa_id=empresa_id, codigo=codigo)
        .filter(ClienteCapacitacion.id != cliente_id)
        .first()
    )
    if dup_cod:
        raise ValueError(f"Ya existe un cliente con el código «{codigo}»")

    dup_nom = (
        ClienteCapacitacion.query.filter_by(empresa_id=empresa_id, activo=True)
        .filter(db.func.lower(ClienteCapacitacion.nombre) == nombre.lower())
        .filter(ClienteCapacitacion.id != cliente_id)
        .first()
    )
    if dup_nom:
        raise ValueError(f"Ya existe un cliente con el nombre «{nombre}»")

    cliente.nombre = nombre
    cliente.codigo = codigo
    db.session.commit()
    return cliente_dict(cliente)


def baja_cliente(empresa_id: int, cliente_id: int) -> dict:
    cliente = obtener_cliente(empresa_id, cliente_id)
    cliente.activo = False
    db.session.commit()
    return {"id": cliente.id, "activo": False}


def ids_participantes_de_cliente(empresa_id: int, cliente_id: int) -> list[int]:
    obtener_cliente(empresa_id, cliente_id)
    rows = (
        db.session.query(ParticipanteCliente.participante_id)
        .join(Participante, Participante.id == ParticipanteCliente.participante_id)
        .filter(ParticipanteCliente.cliente_id == cliente_id)
        .filter(Participante.empresa_id == empresa_id)
        .filter(Participante.activo.is_(True))
        .all()
    )
    return [r[0] for r in rows]


def sync_clientes_participante(empresa_id: int, participante: Participante, cliente_ids) -> None:
    if cliente_ids is None:
        return
    if not isinstance(cliente_ids, (list, tuple, set)):
        cliente_ids = [cliente_ids]
    parsed: list[int] = []
    for raw in cliente_ids:
        if raw in (None, ""):
            continue
        parsed.append(int(raw))
    valid: set[int] = set()
    if parsed:
        valid = {
            c.id
            for c in ClienteCapacitacion.query.filter_by(empresa_id=empresa_id, activo=True)
            .filter(ClienteCapacitacion.id.in_(parsed))
            .all()
        }
    ParticipanteCliente.query.filter_by(participante_id=participante.id).delete()
    for cid in sorted(valid):
        db.session.add(ParticipanteCliente(participante_id=participante.id, cliente_id=cid))
