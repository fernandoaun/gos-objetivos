"""Consultas y mutaciones del módulo Recursos."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload, selectinload

from gos.extensions import db
from gos.modulos.recursos.importer import normalizar_codigo, slug, tipo_desde_interno
from gos.modulos.recursos.models import (
    GRUPO_LABELS,
    TIPO_LABELS,
    TIPOS_UNIDAD,
    RecAsignacion,
    RecCambio,
    RecCentro,
    RecCupo,
    RecDestino,
    RecUnidad,
)

_TZ_AR = timezone(timedelta(hours=-3))


class RecNotFoundError(Exception):
    def __init__(self, message: str = "No encontrado"):
        super().__init__(message)
        self.message = message


class RecValidationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _nombre_destino(dest: RecDestino | None) -> str:
    return dest.nombre if dest is not None else "Sin asignar"


def _fmt_fecha_ar(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_TZ_AR).strftime("%d/%m/%Y %H:%M")


def _registrar_cambio(
    *,
    user_id: int | None,
    accion: str,
    entidad: str,
    resumen: str,
    entidad_id: int | None = None,
) -> None:
    texto = (resumen or "").strip()
    if not texto:
        return
    db.session.add(
        RecCambio(
            user_id=user_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            resumen=texto[:400],
        )
    )


def listar_cambios(*, limit: int = 40) -> list[dict]:
    from gos.models.usuario import Usuario

    limit = max(1, min(int(limit or 40), 100))
    rows = db.session.execute(
        select(RecCambio, Usuario.nombre, Usuario.email)
        .outerjoin(Usuario, Usuario.id == RecCambio.user_id)
        .order_by(RecCambio.created_at.desc())
        .limit(limit)
    ).all()
    out = []
    for cambio, nombre, email in rows:
        quien = (nombre or "").strip() or (email or "").strip() or "Sistema"
        out.append(
            {
                "id": cambio.id,
                "fecha": _fmt_fecha_ar(cambio.created_at),
                "quien": quien,
                "resumen": cambio.resumen,
                "accion": cambio.accion,
                "entidad": cambio.entidad,
            }
        )
    return out


def _destino_dict(dest: RecDestino, *, cupos: dict[str, int] | None = None) -> dict:
    return {
        "id": dest.id,
        "codigo": dest.codigo,
        "nombre": dest.nombre,
        "grupo": dest.grupo,
        "grupo_label": GRUPO_LABELS.get(dest.grupo, dest.grupo),
        "equipo": dest.equipo,
        "orden": dest.orden,
        "activo": dest.activo,
        "cupos": cupos or {},
    }


def listar_destinos(*, activos=True) -> list[RecDestino]:
    stmt = select(RecDestino).options(selectinload(RecDestino.cupos)).order_by(
        RecDestino.orden, RecDestino.nombre
    )
    if activos:
        stmt = stmt.where(RecDestino.activo.is_(True))
    return list(db.session.execute(stmt).scalars().all())


def destinos_payload(*, activos=True) -> list[dict]:
    out = []
    for dest in listar_destinos(activos=activos):
        cupos = {c.tipo: c.necesarias for c in dest.cupos}
        out.append(_destino_dict(dest, cupos=cupos))
    return out


def _es_pendiente(unidad: RecUnidad) -> bool:
    dest = unidad.asignacion.destino if unidad.asignacion else None
    return dest is None


def _es_unidad_de_centro(unidad: RecUnidad, dest: RecDestino | None) -> bool:
    if dest is None:
        return False
    if unidad.es_centro:
        return True
    equipo = (dest.equipo or "").strip()
    if not equipo or equipo.upper() == "GOS":
        return False
    return unidad.codigo == normalizar_codigo(equipo)


def listar_unidades(
    *,
    q: str | None = None,
    tipo: str | None = None,
    destino_id: int | None = None,
    grupo: str | None = None,
    sin_asignar: bool = False,
    activos: bool | None = True,
) -> list[RecUnidad]:
    stmt = select(RecUnidad).options(
        joinedload(RecUnidad.asignacion).joinedload(RecAsignacion.destino)
    )
    if activos is True:
        stmt = stmt.where(RecUnidad.activo.is_(True))
    elif activos is False:
        stmt = stmt.where(RecUnidad.activo.is_(False))
    if tipo:
        stmt = stmt.where(RecUnidad.tipo == tipo.upper())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                RecUnidad.interno.ilike(like),
                RecUnidad.codigo.ilike(like),
                RecUnidad.dominio.ilike(like),
                RecUnidad.contratista.ilike(like),
            )
        )
    unidades = list(db.session.execute(stmt).unique().scalars().all())
    if sin_asignar:
        unidades = [u for u in unidades if _es_pendiente(u)]
    elif destino_id:
        unidades = [
            u for u in unidades if u.asignacion and u.asignacion.destino_id == destino_id
        ]
    elif grupo:
        unidades = [
            u
            for u in unidades
            if u.asignacion and u.asignacion.destino and u.asignacion.destino.grupo == grupo
        ]
    unidades.sort(
        key=lambda u: (
            0 if u.activo and _es_pendiente(u) else 1 if u.activo else 2,
            u.tipo or "",
            u.interno or "",
        )
    )
    return unidades


def unidad_dict(unidad: RecUnidad) -> dict:
    dest = unidad.asignacion.destino if unidad.asignacion else None
    return {
        "id": unidad.id,
        "codigo": unidad.codigo,
        "interno": unidad.interno,
        "dominio": unidad.dominio or "",
        "tipo": unidad.tipo,
        "tipo_label": TIPO_LABELS.get(unidad.tipo, unidad.tipo),
        "contratista": unidad.contratista or "",
        "es_centro": bool(unidad.es_centro),
        "activo": bool(unidad.activo),
        "sin_asignar": _es_pendiente(unidad),
        "destino_id": dest.id if dest else None,
        "destino_nombre": dest.nombre if dest else None,
        "destino_codigo": dest.codigo if dest else None,
        "destino_grupo": dest.grupo if dest else None,
        "equipo": dest.equipo if dest else None,
    }


def asignar_destino(unidad_id: int, destino_id: int | None, *, user_id: int | None = None) -> dict:
    unidad = db.session.get(RecUnidad, unidad_id)
    if unidad is None or not unidad.activo:
        raise RecNotFoundError("Unidad no encontrada")

    actual = unidad.asignacion
    antes = _nombre_destino(actual.destino if actual else None)
    if destino_id in (None, "", 0, "0"):
        if actual is not None:
            db.session.delete(actual)
            _registrar_cambio(
                user_id=user_id,
                accion="asignar",
                entidad="unidad",
                entidad_id=unidad.id,
                resumen=f"{unidad.interno}: {antes} → Sin asignar",
            )
            db.session.commit()
            db.session.refresh(unidad)
        return unidad_dict(unidad)

    dest = db.session.get(RecDestino, int(destino_id))
    if dest is None or not dest.activo:
        raise RecValidationError("Destino no válido")
    if actual is not None and actual.destino_id == dest.id:
        return unidad_dict(unidad)

    if actual is None:
        actual = RecAsignacion(unidad_id=unidad.id, destino_id=dest.id)
        db.session.add(actual)
        unidad.asignacion = actual
    else:
        actual.destino_id = dest.id
    actual.updated_at = datetime.utcnow()
    actual.updated_by = user_id
    _registrar_cambio(
        user_id=user_id,
        accion="asignar",
        entidad="unidad",
        entidad_id=unidad.id,
        resumen=f"{unidad.interno}: {antes} → {dest.nombre}",
    )
    db.session.commit()
    db.session.expire_all()
    unidad = db.session.get(RecUnidad, unidad.id)
    return unidad_dict(unidad)


def crear_unidad(
    *,
    interno: str,
    dominio: str | None = None,
    tipo: str | None = None,
    contratista: str | None = None,
    es_centro: bool = False,
    destino_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    interno_n = re.sub(r"\s+", " ", (interno or "").strip())
    codigo = normalizar_codigo(interno_n)
    if not codigo:
        raise RecValidationError("Indicá el interno de la unidad.")
    tipo_n = (tipo or "").strip().upper() or tipo_desde_interno(interno_n)
    if tipo_n not in TIPOS_UNIDAD:
        raise RecValidationError("Tipo no válido.")
    dominio_n = (dominio or "").strip() or None
    contratista_n = (contratista or "").strip() or None

    existente = db.session.execute(
        select(RecUnidad).where(RecUnidad.codigo == codigo)
    ).scalar_one_or_none()
    if existente is not None:
        if existente.activo:
            raise RecValidationError(f"Ya existe la unidad {existente.interno}.")
        existente.activo = True
        existente.interno = interno_n
        existente.dominio = dominio_n
        existente.tipo = tipo_n
        existente.contratista = contratista_n
        existente.es_centro = bool(es_centro)
        existente.updated_at = datetime.utcnow()
        _registrar_cambio(
            user_id=user_id,
            accion="reactivar",
            entidad="unidad",
            entidad_id=existente.id,
            resumen=f"Reactivó la unidad {existente.interno}",
        )
        db.session.commit()
        if destino_id not in (None, "", 0, "0"):
            return asignar_destino(existente.id, destino_id, user_id=user_id)
        return unidad_dict(existente)

    unidad = RecUnidad(
        codigo=codigo,
        interno=interno_n,
        dominio=dominio_n,
        tipo=tipo_n,
        contratista=contratista_n,
        es_centro=bool(es_centro),
        activo=True,
    )
    db.session.add(unidad)
    db.session.flush()
    _registrar_cambio(
        user_id=user_id,
        accion="alta",
        entidad="unidad",
        entidad_id=unidad.id,
        resumen=f"Alta de unidad {unidad.interno}",
    )
    db.session.commit()
    if destino_id not in (None, "", 0, "0"):
        return asignar_destino(unidad.id, destino_id, user_id=user_id)
    return unidad_dict(unidad)


def dar_de_baja(unidad_id: int, *, user_id: int | None = None) -> dict:
    unidad = db.session.get(RecUnidad, unidad_id)
    if unidad is None:
        raise RecNotFoundError("Unidad no encontrada")
    dest = unidad.asignacion.destino if unidad.asignacion else None
    extra = f" (estaba en {dest.nombre})" if dest is not None else ""
    if unidad.asignacion is not None:
        db.session.delete(unidad.asignacion)
    unidad.activo = False
    unidad.updated_at = datetime.utcnow()
    _registrar_cambio(
        user_id=user_id,
        accion="baja",
        entidad="unidad",
        entidad_id=unidad.id,
        resumen=f"Baja de unidad {unidad.interno}{extra}",
    )
    db.session.commit()
    db.session.refresh(unidad)
    return unidad_dict(unidad)


def reactivar_unidad(unidad_id: int, *, user_id: int | None = None) -> dict:
    unidad = db.session.get(RecUnidad, unidad_id)
    if unidad is None:
        raise RecNotFoundError("Unidad no encontrada")
    unidad.activo = True
    unidad.updated_at = datetime.utcnow()
    _registrar_cambio(
        user_id=user_id,
        accion="reactivar",
        entidad="unidad",
        entidad_id=unidad.id,
        resumen=f"Reactivó la unidad {unidad.interno}",
    )
    db.session.commit()
    return unidad_dict(unidad)


def marcar_centro(unidad_id: int, es_centro: bool, *, user_id: int | None = None) -> dict:
    unidad = db.session.get(RecUnidad, unidad_id)
    if unidad is None or not unidad.activo:
        raise RecNotFoundError("Unidad no encontrada")
    if bool(unidad.es_centro) == bool(es_centro):
        return unidad_dict(unidad)
    unidad.es_centro = bool(es_centro)
    unidad.updated_at = datetime.utcnow()
    if es_centro:
        resumen = f"Marcó {unidad.interno} como unidad de centro"
    else:
        resumen = f"Quitó la marca de centro a {unidad.interno}"
    _registrar_cambio(
        user_id=user_id,
        accion="editar",
        entidad="unidad",
        entidad_id=unidad.id,
        resumen=resumen,
    )
    db.session.commit()
    return unidad_dict(unidad)


def _centro_dict(centro: RecCentro) -> dict:
    dest = centro.destino if centro.destino_id else None
    dest_vivo = dest if dest is not None and dest.activo else None
    return {
        "id": centro.id,
        "codigo": centro.codigo,
        "nombre": centro.nombre or centro.codigo,
        "activo": bool(centro.activo),
        "sin_asignar": dest_vivo is None,
        "destino_id": dest_vivo.id if dest_vivo else None,
        "destino_nombre": dest_vivo.nombre if dest_vivo else None,
        "destino_codigo": dest_vivo.codigo if dest_vivo else None,
    }


def _buscar_centro(codigo: str) -> RecCentro | None:
    return db.session.execute(
        select(RecCentro).where(RecCentro.codigo == codigo)
    ).scalar_one_or_none()


def _asegurar_centro(codigo: str, *, nombre: str | None = None) -> RecCentro:
    centro = _buscar_centro(codigo)
    if centro is None:
        centro = RecCentro(codigo=codigo, nombre=nombre or codigo, activo=True)
        db.session.add(centro)
        db.session.flush()
        return centro
    if not centro.activo:
        centro.activo = True
    if nombre:
        centro.nombre = nombre
    return centro


def _liberar_centros_de_destino(dest: RecDestino) -> None:
    for centro in list(db.session.execute(select(RecCentro).where(RecCentro.destino_id == dest.id)).scalars().all()):
        centro.destino_id = None
        centro.updated_at = datetime.utcnow()
    dest.equipo = None


def _vincular_centro(dest: RecDestino, equipo: str | None, *, forzar: bool = False) -> RecCentro | None:
    equipo_n = (equipo or "").strip() or None
    if equipo_n and equipo_n.upper() == "GOS":
        raise RecValidationError("GOS no se usa como centro de un servicio.")
    actuales = list(
        db.session.execute(select(RecCentro).where(RecCentro.destino_id == dest.id)).scalars().all()
    )
    if not equipo_n:
        _liberar_centros_de_destino(dest)
        return None
    centro = _asegurar_centro(equipo_n)
    if centro.destino_id not in (None, dest.id):
        ocupado = db.session.get(RecDestino, centro.destino_id)
        if not forzar:
            nombre = ocupado.nombre if ocupado else "otro servicio"
            raise RecValidationError(f"El centro {equipo_n} ya está en {nombre}.")
        if ocupado is not None and (ocupado.equipo or "").strip() == centro.codigo:
            ocupado.equipo = None
        centro.destino_id = None
    for otro in actuales:
        if otro.id != centro.id:
            otro.destino_id = None
            otro.updated_at = datetime.utcnow()
    centro.destino_id = dest.id
    centro.updated_at = datetime.utcnow()
    dest.equipo = centro.codigo
    return centro


def listar_centros(*, activos: bool | None = True) -> list[RecCentro]:
    stmt = select(RecCentro).options(joinedload(RecCentro.destino)).order_by(RecCentro.codigo)
    if activos is True:
        stmt = stmt.where(RecCentro.activo.is_(True))
    elif activos is False:
        stmt = stmt.where(RecCentro.activo.is_(False))
    rows = list(db.session.execute(stmt).unique().scalars().all())
    rows.sort(
        key=lambda c: (
            0 if c.activo else 1,
            0 if not (c.destino_id and c.destino and c.destino.activo) else 1,
            c.codigo or "",
        )
    )
    return rows


def centros_payload(*, activos: bool | None = True) -> list[dict]:
    return [_centro_dict(c) for c in listar_centros(activos=activos)]


def crear_centro(
    *,
    codigo: str,
    nombre: str | None = None,
    destino_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    codigo_n = (codigo or "").strip()
    if not codigo_n:
        raise RecValidationError("Indicá el código del centro (H18, H23, …).")
    if codigo_n.upper() == "GOS":
        raise RecValidationError("GOS no se usa como centro.")
    existente = _buscar_centro(codigo_n)
    if existente is not None and existente.activo:
        raise RecValidationError(f"Ya existe el centro {existente.codigo}.")
    if existente is not None:
        existente.activo = True
        existente.nombre = (nombre or "").strip() or existente.nombre or codigo_n
        existente.updated_at = datetime.utcnow()
        centro = existente
    else:
        centro = RecCentro(
            codigo=codigo_n,
            nombre=(nombre or "").strip() or codigo_n,
            activo=True,
        )
        db.session.add(centro)
        db.session.flush()
    if destino_id not in (None, "", 0, "0"):
        dest = db.session.get(RecDestino, int(destino_id))
        if dest is None or not dest.activo or dest.grupo != "servicio":
            raise RecValidationError("Servicio no válido.")
        _vincular_centro(dest, centro.codigo, forzar=True)
    else:
        centro.destino_id = None
    extra = ""
    dest_vivo = centro.destino if centro.destino_id else None
    if dest_vivo is not None and dest_vivo.activo:
        extra = f" en {dest_vivo.nombre}"
    _registrar_cambio(
        user_id=user_id,
        accion="alta",
        entidad="centro",
        entidad_id=centro.id,
        resumen=f"Alta de centro {centro.codigo}{extra}",
    )
    db.session.commit()
    return _centro_dict(centro)


def actualizar_centro(
    centro_id: int,
    *,
    codigo: str | None = None,
    nombre: str | None = None,
    destino_id: int | None = None,
    tocar_destino: bool = False,
    user_id: int | None = None,
) -> dict:
    centro = db.session.get(RecCentro, int(centro_id))
    if centro is None or not centro.activo:
        raise RecNotFoundError("Centro no encontrado")
    partes: list[str] = []
    if codigo is not None:
        codigo_n = codigo.strip()
        if not codigo_n:
            raise RecValidationError("Indicá el código del centro.")
        if codigo_n.upper() == "GOS":
            raise RecValidationError("GOS no se usa como centro.")
        otro = _buscar_centro(codigo_n)
        if otro is not None and otro.id != centro.id:
            raise RecValidationError(f"Ya existe el centro {codigo_n}.")
        old = centro.codigo
        if old != codigo_n:
            partes.append(f"código {old} → {codigo_n}")
        centro.codigo = codigo_n
        if centro.destino_id:
            dest = db.session.get(RecDestino, centro.destino_id)
            if dest is not None and (dest.equipo or "") == old:
                dest.equipo = codigo_n
    if nombre is not None:
        nombre_n = nombre.strip() or centro.codigo
        if nombre_n != (centro.nombre or ""):
            partes.append(f"nombre {centro.nombre} → {nombre_n}")
        centro.nombre = nombre_n
    if tocar_destino:
        dest_antes = db.session.get(RecDestino, centro.destino_id) if centro.destino_id else None
        if destino_id in (None, "", 0, "0"):
            dest = db.session.get(RecDestino, centro.destino_id) if centro.destino_id else None
            centro.destino_id = None
            if dest is not None and (dest.equipo or "").strip() == centro.codigo:
                dest.equipo = None
            if dest_antes is not None:
                partes.append(f"{_nombre_destino(dest_antes)} → Sin asignar")
        else:
            dest = db.session.get(RecDestino, int(destino_id))
            if dest is None or not dest.activo or dest.grupo != "servicio":
                raise RecValidationError("Servicio no válido.")
            _vincular_centro(dest, centro.codigo, forzar=True)
            if dest_antes is None or dest_antes.id != dest.id:
                partes.append(f"{_nombre_destino(dest_antes)} → {dest.nombre}")
    centro.updated_at = datetime.utcnow()
    if partes:
        _registrar_cambio(
            user_id=user_id,
            accion="editar",
            entidad="centro",
            entidad_id=centro.id,
            resumen=f"{centro.codigo}: " + " · ".join(partes),
        )
    db.session.commit()
    return _centro_dict(centro)


def dar_de_baja_centro(centro_id: int, *, user_id: int | None = None) -> dict:
    centro = db.session.get(RecCentro, int(centro_id))
    if centro is None:
        raise RecNotFoundError("Centro no encontrado")
    dest = db.session.get(RecDestino, centro.destino_id) if centro.destino_id else None
    extra = f" (estaba en {dest.nombre})" if dest is not None else ""
    if dest is not None and (dest.equipo or "").strip() == centro.codigo:
        dest.equipo = None
    centro.destino_id = None
    centro.activo = False
    centro.updated_at = datetime.utcnow()
    _registrar_cambio(
        user_id=user_id,
        accion="baja",
        entidad="centro",
        entidad_id=centro.id,
        resumen=f"Baja de centro {centro.codigo}{extra}",
    )
    db.session.commit()
    return _centro_dict(centro)


def reactivar_centro(centro_id: int, *, user_id: int | None = None) -> dict:
    centro = db.session.get(RecCentro, int(centro_id))
    if centro is None:
        raise RecNotFoundError("Centro no encontrado")
    centro.activo = True
    centro.updated_at = datetime.utcnow()
    _registrar_cambio(
        user_id=user_id,
        accion="reactivar",
        entidad="centro",
        entidad_id=centro.id,
        resumen=f"Reactivó el centro {centro.codigo}",
    )
    db.session.commit()
    return _centro_dict(centro)


def dar_de_baja_servicio(destino_id: int, *, user_id: int | None = None) -> dict:
    dest = db.session.get(RecDestino, int(destino_id))
    if dest is None:
        raise RecNotFoundError("Servicio no encontrado")
    if dest.grupo != "servicio":
        raise RecValidationError("Solo se dan de baja los servicios.")
    nombre = dest.nombre
    _liberar_centros_de_destino(dest)
    asignaciones = list(
        db.session.execute(select(RecAsignacion).where(RecAsignacion.destino_id == dest.id)).scalars().all()
    )
    for asig in asignaciones:
        db.session.delete(asig)
    dest.activo = False
    _registrar_cambio(
        user_id=user_id,
        accion="baja",
        entidad="servicio",
        entidad_id=dest.id,
        resumen=f"Baja de servicio {nombre}",
    )
    db.session.commit()
    return _destino_dict(dest)


def _unidades_de_centro_en(dest: RecDestino) -> list[RecUnidad]:
    stmt = (
        select(RecUnidad)
        .options(joinedload(RecUnidad.asignacion).joinedload(RecAsignacion.destino))
        .where(RecUnidad.activo.is_(True))
    )
    out: list[RecUnidad] = []
    for unidad in db.session.execute(stmt).unique().scalars().all():
        if (
            unidad.asignacion
            and unidad.asignacion.destino_id == dest.id
            and _es_unidad_de_centro(unidad, dest)
        ):
            out.append(unidad)
    return out


def mover_equipo(
    equipo: str,
    destino_id: int | None,
    *,
    desde_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    equipo_n = (equipo or "").strip()
    if not equipo_n or equipo_n.upper() == "GOS":
        raise RecValidationError("Indicá un centro válido.")

    dest = None
    if destino_id not in (None, "", 0, "0"):
        dest = db.session.get(RecDestino, int(destino_id))
        if dest is None or not dest.activo:
            raise RecNotFoundError("Servicio no encontrado")
        if dest.grupo != "servicio":
            raise RecValidationError("El centro solo se asigna a un servicio.")

    centro = _asegurar_centro(equipo_n)

    origen = None
    if desde_id not in (None, "", 0, "0"):
        origen = db.session.get(RecDestino, int(desde_id))
    if origen is None and centro.destino_id:
        origen = db.session.get(RecDestino, centro.destino_id)
    if origen is None:
        origen = db.session.execute(
            select(RecDestino).where(
                RecDestino.equipo == equipo_n,
                RecDestino.activo.is_(True),
            )
        ).scalars().first()

    if dest is not None and origen is not None and origen.id == dest.id:
        return {
            "ok": True,
            "equipo": dest.equipo,
            "destino_id": dest.id,
            "origen_id": origen.id,
        }

    acompanan = _unidades_de_centro_en(origen) if origen is not None else []

    if dest is None:
        if origen is not None and (origen.equipo or "").strip() == equipo_n:
            origen.equipo = None
        centro.destino_id = None
        centro.updated_at = datetime.utcnow()
        for unidad in acompanan:
            if unidad.asignacion is None:
                continue
            db.session.delete(unidad.asignacion)
        _registrar_cambio(
            user_id=user_id,
            accion="mover",
            entidad="centro",
            entidad_id=centro.id,
            resumen=f"Centro {equipo_n}: {_nombre_destino(origen)} → Sin asignar",
        )
        db.session.commit()
        return {
            "ok": True,
            "equipo": equipo_n,
            "destino_id": None,
            "origen_id": origen.id if origen else None,
            "origen_equipo": origen.equipo if origen else None,
        }

    _vincular_centro(dest, equipo_n, forzar=True)
    if origen is not None and origen.id != dest.id and (origen.equipo or "").strip() == equipo_n:
        origen.equipo = None
    for unidad in acompanan:
        if unidad.asignacion is None:
            continue
        unidad.asignacion.destino_id = dest.id
        unidad.asignacion.updated_at = datetime.utcnow()
        unidad.asignacion.updated_by = user_id
    for otro in listar_destinos(activos=False):
        if otro.id == dest.id:
            continue
        if (otro.equipo or "").strip() == equipo_n:
            otro.equipo = None
    _registrar_cambio(
        user_id=user_id,
        accion="mover",
        entidad="centro",
        entidad_id=centro.id,
        resumen=f"Centro {equipo_n}: {_nombre_destino(origen)} → {dest.nombre}",
    )
    db.session.commit()
    return {
        "ok": True,
        "equipo": dest.equipo,
        "destino_id": dest.id,
        "destino_nombre": dest.nombre,
        "origen_id": origen.id if origen else None,
        "origen_equipo": origen.equipo if origen else None,
    }


def _cupos_payload(raw) -> dict[str, int]:
    data = raw if isinstance(raw, dict) else {}
    out: dict[str, int] = {}
    for tipo in TIPOS_UNIDAD:
        try:
            out[tipo] = max(0, int(data.get(tipo) or 0))
        except (TypeError, ValueError):
            out[tipo] = 0
    return out


def _codigo_servicio_unico(base: str) -> str:
    codigo = slug(base) or "SERVICIO"
    if db.session.execute(select(RecDestino).where(RecDestino.codigo == codigo)).scalar_one_or_none() is None:
        return codigo
    n = 2
    while True:
        cand = f"{codigo}-{n}"
        if db.session.execute(select(RecDestino).where(RecDestino.codigo == cand)).scalar_one_or_none() is None:
            return cand
        n += 1


def _set_cupos(dest: RecDestino, cupos: dict[str, int]) -> None:
    actuales = {c.tipo: c for c in dest.cupos}
    for tipo in TIPOS_UNIDAD:
        nec = int(cupos.get(tipo) or 0)
        if tipo in actuales:
            actuales[tipo].necesarias = nec
        else:
            dest.cupos.append(RecCupo(tipo=tipo, necesarias=nec))


def _diff_cupos(antes: dict[str, int], despues: dict[str, int]) -> list[str]:
    partes: list[str] = []
    for tipo in TIPOS_UNIDAD:
        old = int(antes.get(tipo) or 0)
        new = int(despues.get(tipo) or 0)
        if old != new:
            partes.append(f"{tipo} nec. {old} → {new}")
    return partes


def crear_servicio(
    *,
    nombre: str,
    equipo: str | None = None,
    cupos: dict | None = None,
    user_id: int | None = None,
) -> dict:
    nombre_n = re.sub(r"\s+", " ", (nombre or "").strip())
    if not nombre_n:
        raise RecValidationError("Indicá el nombre del servicio.")
    equipo_n = (equipo or "").strip() or None
    if equipo_n and equipo_n.upper() == "GOS":
        raise RecValidationError("GOS no se usa como centro de un servicio.")
    if equipo_n:
        tomado = db.session.execute(
            select(RecDestino).where(
                RecDestino.activo.is_(True),
                RecDestino.equipo == equipo_n,
            )
        ).scalar_one_or_none()
        if tomado is not None:
            raise RecValidationError(f"El centro {equipo_n} ya está en {tomado.nombre}.")

    cupos_n = _cupos_payload(cupos)
    max_orden = db.session.execute(
        select(RecDestino.orden).where(RecDestino.grupo == "servicio")
    ).scalars().all()
    dest = RecDestino(
        codigo=_codigo_servicio_unico(nombre_n),
        nombre=nombre_n,
        grupo="servicio",
        equipo=None,
        orden=(max(max_orden) + 1) if max_orden else 0,
        activo=True,
        columna_excel=None,
    )
    _set_cupos(dest, cupos_n)
    db.session.add(dest)
    db.session.flush()
    _vincular_centro(dest, equipo_n)
    extra = []
    if dest.equipo:
        extra.append(f"centro {dest.equipo}")
    nec = [f"{t} {n}" for t, n in cupos_n.items() if n]
    if nec:
        extra.append("nec. " + ", ".join(nec))
    sufijo = (" · " + " · ".join(extra)) if extra else ""
    _registrar_cambio(
        user_id=user_id,
        accion="alta",
        entidad="servicio",
        entidad_id=dest.id,
        resumen=f"Alta de servicio {dest.nombre}{sufijo}",
    )
    db.session.commit()
    return _destino_dict(dest, cupos=cupos_n)


def actualizar_servicio(
    destino_id: int,
    *,
    nombre: str | None = None,
    equipo: str | None = None,
    cupos: dict | None = None,
    user_id: int | None = None,
) -> dict:
    dest = db.session.get(RecDestino, int(destino_id))
    if dest is None or not dest.activo:
        raise RecNotFoundError("Destino no encontrado")
    partes: list[str] = []
    equipo_antes = (dest.equipo or "").strip() or None
    cupos_antes = {c.tipo: int(c.necesarias or 0) for c in dest.cupos}
    if dest.grupo == "servicio":
        if nombre is not None:
            nombre_n = re.sub(r"\s+", " ", nombre.strip())
            if not nombre_n:
                raise RecValidationError("Indicá el nombre del servicio.")
            if nombre_n != dest.nombre:
                partes.append(f"nombre {dest.nombre} → {nombre_n}")
            dest.nombre = nombre_n
        if equipo is not None:
            _vincular_centro(dest, equipo)
            equipo_despues = (dest.equipo or "").strip() or None
            if (equipo_antes or "") != (equipo_despues or ""):
                partes.append(
                    f"centro {equipo_antes or 'sin centro'} → {equipo_despues or 'sin centro'}"
                )
    elif cupos is None:
        raise RecValidationError("Solo se editan las unidades necesarias de esta columna.")
    if cupos is not None:
        cupos_n = _cupos_payload(cupos)
        _set_cupos(dest, cupos_n)
        partes.extend(_diff_cupos(cupos_antes, cupos_n))
    if partes:
        _registrar_cambio(
            user_id=user_id,
            accion="editar",
            entidad="servicio",
            entidad_id=dest.id,
            resumen=f"{dest.nombre}: " + " · ".join(partes),
        )
    db.session.commit()
    actuales = {c.tipo: c.necesarias for c in dest.cupos}
    return _destino_dict(dest, cupos=actuales)


def resumen() -> dict:
    destinos = listar_destinos(activos=True)
    unidades = listar_unidades(activos=True)
    por_tipo = {t: 0 for t in TIPOS_UNIDAD}
    por_grupo = {"servicio": 0, "estructura": 0, "estado": 0}
    libres = 0
    reparacion = 0
    fuera = 0
    sin_asignar = 0
    afectadas_por = defaultdict(lambda: defaultdict(int))  # destino_id -> tipo -> n
    centros_por = defaultdict(list)
    unidades_por = defaultdict(list)
    sin_asignar_flota = []

    def _chip(unidad: RecUnidad, dest: RecDestino | None = None) -> dict:
        return {
            "id": unidad.id,
            "interno": unidad.interno,
            "tipo": unidad.tipo,
            "dominio": unidad.dominio or "",
            "es_centro": _es_unidad_de_centro(unidad, dest) if dest else bool(unidad.es_centro),
        }

    for u in unidades:
        por_tipo[u.tipo] = por_tipo.get(u.tipo, 0) + 1
        dest = u.asignacion.destino if u.asignacion else None
        if dest is None:
            sin_asignar += 1
            sin_asignar_flota.append(_chip(u))
            continue
        por_grupo[dest.grupo] = por_grupo.get(dest.grupo, 0) + 1
        unidades_por[dest.id].append(_chip(u, dest))
        if _es_unidad_de_centro(u, dest):
            centros_por[dest.id].append(
                {
                    "id": u.id,
                    "interno": u.interno,
                    "tipo": u.tipo,
                    "dominio": u.dominio or "",
                    "es_centro": True,
                }
            )
        else:
            afectadas_por[dest.id][u.tipo] += 1
        slug = (dest.codigo or "").upper()
        if slug == "LIBRE":
            libres += 1
        elif slug == "REPARACION":
            reparacion += 1
        elif slug.startswith("FUERA"):
            fuera += 1

    huecos = []
    por_grupo_cards = {"servicio": [], "estructura": [], "estado": []}
    necesarias_serv = 0
    afectadas_serv = 0

    for dest in destinos:
        cupos = {c.tipo: c.necesarias for c in dest.cupos}
        tipos_detalle = []
        dest_faltantes = 0
        dest_afectadas = 0
        dest_necesarias = 0
        for tipo in TIPOS_UNIDAD:
            nec = int(cupos.get(tipo) or 0)
            af = int(afectadas_por[dest.id].get(tipo) or 0)
            delta = af - nec
            tipos_detalle.append(
                {
                    "tipo": tipo,
                    "label": TIPO_LABELS[tipo],
                    "necesarias": nec,
                    "afectadas": af,
                    "delta": delta,
                }
            )
            dest_necesarias += nec
            dest_afectadas += af
            if delta < 0:
                dest_faltantes += -delta
                huecos.append(
                    {
                        "destino_id": dest.id,
                        "destino": dest.nombre,
                        "equipo": dest.equipo,
                        "grupo": dest.grupo,
                        "tipo": tipo,
                        "tipo_label": TIPO_LABELS[tipo],
                        "necesarias": nec,
                        "afectadas": af,
                        "faltan": -delta,
                    }
                )
        slug = (dest.codigo or "").upper()
        equipo_norm = normalizar_codigo(dest.equipo or "")
        centros_visibles = [
            c
            for c in centros_por[dest.id]
            if normalizar_codigo(c["interno"]) != equipo_norm
        ]
        ids_centro = {c["id"] for c in centros_visibles}
        equipo_ok = bool((dest.equipo or "").strip()) and (dest.equipo or "").upper() != "GOS"
        sin_centro = dest.grupo == "servicio" and not equipo_ok
        alerta_columna = any(int(row["delta"]) < 0 for row in tipos_detalle)
        card = {
            **_destino_dict(dest, cupos=cupos),
            "centros": centros_visibles,
            "flota": [u for u in unidades_por[dest.id] if u["id"] not in ids_centro],
            "tipos": tipos_detalle,
            "necesarias": dest_necesarias,
            "afectadas": dest_afectadas,
            "faltantes": dest_faltantes,
            "sin_centro": sin_centro,
            "alerta_columna": alerta_columna,
            "ok": dest_faltantes == 0 and not sin_centro,
            "tono": (
                "libre"
                if slug == "LIBRE"
                else "reparacion"
                if slug == "REPARACION"
                else "fuera"
                if slug.startswith("FUERA")
                else dest.grupo
            ),
        }
        por_grupo_cards.setdefault(dest.grupo, []).append(card)
        if dest.grupo == "servicio":
            necesarias_serv += dest_necesarias
            afectadas_serv += dest_afectadas

    parque_cols = por_grupo_cards["estructura"] + por_grupo_cards["estado"]
    parque_nec = {t: 0 for t in TIPOS_UNIDAD}
    parque_af = {t: 0 for t in TIPOS_UNIDAD}
    for card in parque_cols:
        for row in card["tipos"]:
            parque_nec[row["tipo"]] += int(row["necesarias"] or 0)
            parque_af[row["tipo"]] += int(row["afectadas"] or 0)

    total_tipos = []
    total_faltantes = 0
    for tipo in TIPOS_UNIDAD:
        nec = parque_nec[tipo]
        af = parque_af[tipo]
        delta = af - nec
        total_tipos.append(
            {
                "tipo": tipo,
                "label": TIPO_LABELS[tipo],
                "necesarias": nec,
                "afectadas": af,
                "delta": delta,
            }
        )
        if delta < 0:
            total_faltantes += -delta

    total_card = {
        "id": None,
        "codigo": "TOTAL",
        "nombre": "TOTAL",
        "grupo": "total",
        "grupo_label": "Total",
        "equipo": None,
        "orden": 999,
        "activo": True,
        "cupos": parque_nec,
        "centros": [],
        "flota": [],
        "tipos": total_tipos,
        "necesarias": sum(parque_nec.values()),
        "afectadas": sum(parque_af.values()),
        "faltantes": total_faltantes,
        "ok": total_faltantes == 0,
        "sin_centro": False,
        "alerta_columna": total_faltantes > 0,
        "tono": "total",
    }

    huecos.sort(key=lambda h: (-h["faltan"], h["destino"]))
    por_grupo_cards["servicio"].sort(
        key=lambda s: (
            0 if s.get("sin_centro") else 1 if not s.get("ok") else 2,
            s.get("orden") or 0,
            s.get("nombre") or "",
        )
    )
    total = len(unidades)
    cubierto = round(100 * afectadas_serv / necesarias_serv, 1) if necesarias_serv else None
    sin_asignar_centros = [
        _centro_dict(c)
        for c in listar_centros(activos=True)
        if c.destino_id is None or not (c.destino and c.destino.activo)
    ]

    return {
        "unidades": total,
        "asignadas": total - sin_asignar,
        "sin_asignar": sin_asignar,
        "sin_asignar_flota": sin_asignar_flota,
        "sin_asignar_centros": sin_asignar_centros,
        "por_tipo": por_tipo,
        "por_grupo": por_grupo,
        "libres": libres,
        "reparacion": reparacion,
        "fuera": fuera,
        "huecos": huecos,
        "faltantes": sum(h["faltan"] for h in huecos),
        "servicios": por_grupo_cards["servicio"],
        "estructura": por_grupo_cards["estructura"],
        "estados": por_grupo_cards["estado"],
        "parque_columnas": por_grupo_cards["estructura"]
        + por_grupo_cards["estado"]
        + [total_card],
        "total": total_card,
        "necesarias_servicios": necesarias_serv,
        "afectadas_servicios": afectadas_serv,
        "cobertura_servicios": cubierto,
        "tipo_labels": TIPO_LABELS,
        "grupo_labels": GRUPO_LABELS,
    }


_GRUPO_TABLERO = (
    ("servicio", "Servicios", "servicios"),
    ("estructura", "Estructura GOS", "estructura"),
    ("estado", "Estado de parque", "estados"),
)
_GRUPO_ORDEN = {"servicio": 0, "estructura": 1, "estado": 2}


def _unidades_de_card(card: dict) -> list[dict]:
    return list(card.get("centros") or []) + list(card.get("flota") or [])


def _destino_resumen(card: dict) -> dict:
    unidades = _unidades_de_card(card)
    tipos = [
        t
        for t in (card.get("tipos") or [])
        if int(t.get("necesarias") or 0) or int(t.get("afectadas") or 0)
    ]
    return {
        "id": card.get("id"),
        "nombre": card.get("nombre"),
        "codigo": card.get("codigo"),
        "grupo": card.get("grupo"),
        "grupo_label": card.get("grupo_label") or GRUPO_LABELS.get(card.get("grupo") or "", ""),
        "equipo": card.get("equipo"),
        "faltantes": int(card.get("faltantes") or 0),
        "necesarias": int(card.get("necesarias") or 0),
        "afectadas": int(card.get("afectadas") or 0),
        "unidades": unidades,
        "tipos": tipos,
        "n": len(unidades),
    }


def detalle_tablero(data: dict) -> dict:
    """Desglose clickeable del tablero: unidades por tipo, grupo y hueco."""
    destinos_cards = (
        list(data.get("servicios") or [])
        + list(data.get("estructura") or [])
        + list(data.get("estados") or [])
    )
    destinos_by_id = {c["id"]: c for c in destinos_cards if c.get("id")}
    sin_asignar_flota = list(data.get("sin_asignar_flota") or [])

    tipos: dict[str, dict] = {}
    for tipo, label in TIPO_LABELS.items():
        por_destino = []
        for card in destinos_cards:
            units = [u for u in _unidades_de_card(card) if u.get("tipo") == tipo]
            if not units:
                continue
            por_destino.append(
                {
                    "id": card.get("id"),
                    "nombre": card.get("nombre"),
                    "codigo": card.get("codigo"),
                    "grupo": card.get("grupo"),
                    "grupo_label": card.get("grupo_label")
                    or GRUPO_LABELS.get(card.get("grupo") or "", ""),
                    "equipo": card.get("equipo"),
                    "unidades": units,
                    "n": len(units),
                }
            )
        por_destino.sort(
            key=lambda d: (_GRUPO_ORDEN.get(d.get("grupo") or "", 9), d.get("nombre") or "")
        )
        sin_asig = [u for u in sin_asignar_flota if u.get("tipo") == tipo]
        tipos[tipo] = {
            "tipo": tipo,
            "label": label,
            "total": int((data.get("por_tipo") or {}).get(tipo) or 0),
            "destinos": por_destino,
            "sin_asignar": sin_asig,
        }

    grupos: dict[str, dict] = {}
    for grupo, label, clave in _GRUPO_TABLERO:
        cards = list(data.get(clave) or [])
        grupos[grupo] = {
            "grupo": grupo,
            "label": label,
            "total": int((data.get("por_grupo") or {}).get(grupo) or 0),
            "destinos": [_destino_resumen(c) for c in cards],
        }
    grupos["none"] = {
        "grupo": "none",
        "label": "Sin asignar",
        "total": int(data.get("sin_asignar") or 0),
        "unidades": sin_asignar_flota,
        "centros": list(data.get("sin_asignar_centros") or []),
        "hint": (
            f"{int(data.get('libres') or 0)} libres · "
            f"{int(data.get('reparacion') or 0)} reparación · "
            f"{int(data.get('fuera') or 0)} fuera de servicio"
        ),
    }

    huecos = []
    for h in data.get("huecos") or []:
        card = destinos_by_id.get(h.get("destino_id")) or {}
        flota = list(card.get("flota") or [])
        centros = list(card.get("centros") or [])
        del_tipo = [u for u in flota if u.get("tipo") == h.get("tipo")]
        otras = [u for u in flota if u.get("tipo") != h.get("tipo")]
        huecos.append(
            {
                "destino_id": h.get("destino_id"),
                "destino": h.get("destino"),
                "equipo": h.get("equipo"),
                "grupo": h.get("grupo"),
                "tipo": h.get("tipo"),
                "tipo_label": h.get("tipo_label") or TIPO_LABELS.get(h.get("tipo") or "", ""),
                "necesarias": int(h.get("necesarias") or 0),
                "afectadas": int(h.get("afectadas") or 0),
                "faltan": int(h.get("faltan") or 0),
                "unidades": del_tipo,
                "otras": otras,
                "centros": centros,
            }
        )

    destinos_con_unidades = [_destino_resumen(c) for c in destinos_cards if _unidades_de_card(c)]
    return {
        "tipos": tipos,
        "grupos": grupos,
        "huecos": huecos,
        "kpis": {
            "unidades": {
                "label": "Unidades",
                "total": int(data.get("unidades") or 0),
                "hint": f"{int(data.get('asignadas') or 0)} con destino",
                "destinos": destinos_con_unidades,
                "sin_asignar": sin_asignar_flota,
            },
            "cobertura": {
                "label": "Cobertura servicios",
                "total": data.get("cobertura_servicios"),
                "hint": (
                    f"{int(data.get('afectadas_servicios') or 0)} / "
                    f"{int(data.get('necesarias_servicios') or 0)} cupos"
                ),
                "destinos": [_destino_resumen(c) for c in (data.get("servicios") or [])],
            },
            "faltantes": {
                "label": "Faltantes",
                "total": int(data.get("faltantes") or 0),
                "huecos": huecos,
            },
            "sin_asignar": grupos["none"],
        },
    }
