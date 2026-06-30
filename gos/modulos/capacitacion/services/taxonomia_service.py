from __future__ import annotations

import re
from collections import defaultdict

from gos.extensions import db
from gos.modulos.capacitacion.models.taxonomia import CASCADA_CAPACITACION
from gos.modulos.capacitacion.models.taxonomia_item import NIVELES_TAXONOMIA, TaxonomiaItem

_PADRE_NIVEL = {
    "tipo": "categoria",
    "origen": "tipo",
    "modalidad": "origen",
}


def _slug_codigo(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower())
    return (s.strip("_") or "item")[:30]


def _crear_o_obtener_item(
    empresa_id: int,
    *,
    nivel: str,
    parent_id: int | None,
    codigo: str,
    nombre: str,
    orden: int,
) -> TaxonomiaItem:
    item = TaxonomiaItem.query.filter_by(
        empresa_id=empresa_id,
        nivel=nivel,
        parent_id=parent_id,
        codigo=codigo,
        activo=True,
    ).first()
    if item:
        return item
    item = TaxonomiaItem(
        empresa_id=empresa_id,
        nivel=nivel,
        parent_id=parent_id,
        codigo=codigo,
        nombre=nombre,
        orden=orden,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _sembrar_cascada(empresa_id: int) -> None:
    orden_cat = 0
    for cat_codigo, cat in CASCADA_CAPACITACION.items():
        cat_row = _crear_o_obtener_item(
            empresa_id,
            nivel="categoria",
            parent_id=None,
            codigo=cat_codigo,
            nombre=cat["label"],
            orden=orden_cat,
        )
        orden_cat += 1
        orden_tipo = 0
        for tipo_codigo, tipo in cat.get("tipos", {}).items():
            tipo_row = _crear_o_obtener_item(
                empresa_id,
                nivel="tipo",
                parent_id=cat_row.id,
                codigo=tipo_codigo,
                nombre=tipo["label"],
                orden=orden_tipo,
            )
            orden_tipo += 1
            orden_origen = 0
            for origen_codigo, origen in tipo.get("origenes", {}).items():
                origen_row = _crear_o_obtener_item(
                    empresa_id,
                    nivel="origen",
                    parent_id=tipo_row.id,
                    codigo=origen_codigo,
                    nombre=origen["label"],
                    orden=orden_origen,
                )
                orden_origen += 1
                orden_mod = 0
                for mod_codigo in origen.get("modalidades", ()):
                    labels = {"presencial": "Presencial", "virtual": "Virtual", "mixta": "Mixta"}
                    _crear_o_obtener_item(
                        empresa_id,
                        nivel="modalidad",
                        parent_id=origen_row.id,
                        codigo=mod_codigo,
                        nombre=labels.get(mod_codigo, mod_codigo.replace("_", " ").title()),
                        orden=orden_mod,
                    )
                    orden_mod += 1


def ensure_taxonomia_defaults(empresa_id: int) -> None:
    if not TaxonomiaItem.query.filter_by(empresa_id=empresa_id).first():
        _sembrar_cascada(empresa_id)
        db.session.commit()
        return
    _sembrar_cascada(empresa_id)
    db.session.commit()


def _items_activos(empresa_id: int) -> list[TaxonomiaItem]:
    ensure_taxonomia_defaults(empresa_id)
    return (
        TaxonomiaItem.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(TaxonomiaItem.orden, TaxonomiaItem.nombre)
        .all()
    )


def arbol_taxonomia(empresa_id: int) -> dict:
    items = _items_activos(empresa_id)
    by_parent: dict[int | None, list[TaxonomiaItem]] = defaultdict(list)
    for item in items:
        by_parent[item.parent_id].append(item)

    cascada: dict = {}
    for cat in by_parent[None]:
        if cat.nivel != "categoria":
            continue
        tipos_dict: dict = {}
        for tipo in by_parent.get(cat.id, []):
            if tipo.nivel != "tipo":
                continue
            origenes_dict: dict = {}
            for origen in by_parent.get(tipo.id, []):
                if origen.nivel != "origen":
                    continue
                modals = [m for m in by_parent.get(origen.id, []) if m.nivel == "modalidad"]
                origenes_dict[origen.codigo] = {
                    "label": origen.nombre,
                    "modalidades": [m.codigo for m in modals],
                    "modalidad_labels": {m.codigo: m.nombre for m in modals},
                }
            tipos_dict[tipo.codigo] = {"label": tipo.nombre, "origenes": origenes_dict}
        cascada[cat.codigo] = {"label": cat.nombre, "tipos": tipos_dict}
    return cascada


def listar_taxonomia_items(
    empresa_id: int,
    *,
    nivel: str | None = None,
    parent_id: int | None = None,
) -> list[dict]:
    ensure_taxonomia_defaults(empresa_id)
    q = TaxonomiaItem.query.filter_by(empresa_id=empresa_id, activo=True)
    if nivel:
        q = q.filter_by(nivel=nivel)
    if parent_id is not None:
        q = q.filter_by(parent_id=parent_id if parent_id else None)
    elif nivel == "categoria":
        q = q.filter(TaxonomiaItem.parent_id.is_(None))
    items = q.order_by(TaxonomiaItem.orden, TaxonomiaItem.nombre).all()
    return [_item_dict(i) for i in items]


def crear_taxonomia_item(empresa_id: int, data: dict) -> dict:
    nivel = (data.get("nivel") or "").strip().lower()
    if nivel not in NIVELES_TAXONOMIA:
        raise ValueError("Nivel inválido (categoria, tipo, origen o modalidad)")

    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre es obligatorio")

    codigo = (data.get("codigo") or "").strip().lower() or _slug_codigo(nombre)
    parent_id = data.get("parent_id")
    parent_id = int(parent_id) if parent_id not in (None, "", 0) else None

    if nivel == "categoria":
        parent_id = None
    elif not parent_id:
        raise ValueError("Debe indicar el ítem padre")

    if parent_id:
        parent = TaxonomiaItem.query.filter_by(
            id=parent_id, empresa_id=empresa_id, activo=True
        ).first()
        if not parent:
            raise ValueError("Ítem padre no encontrado")
        esperado = _PADRE_NIVEL.get(nivel)
        if parent.nivel != esperado:
            raise ValueError(f"El padre debe ser de nivel «{esperado}»")

    dup = TaxonomiaItem.query.filter_by(
        empresa_id=empresa_id, nivel=nivel, parent_id=parent_id, codigo=codigo, activo=True
    ).first()
    if dup:
        raise ValueError(f"Ya existe un ítem con el código «{codigo}» en este nivel")

    orden = TaxonomiaItem.query.filter_by(
        empresa_id=empresa_id, nivel=nivel, parent_id=parent_id, activo=True
    ).count()

    item = TaxonomiaItem(
        empresa_id=empresa_id,
        nivel=nivel,
        parent_id=parent_id,
        codigo=codigo,
        nombre=nombre,
        orden=orden,
    )
    db.session.add(item)
    db.session.commit()
    return _item_dict(item)


def actualizar_taxonomia_item(empresa_id: int, item_id: int, data: dict) -> dict:
    item = TaxonomiaItem.query.filter_by(id=item_id, empresa_id=empresa_id, activo=True).first()
    if not item:
        raise ValueError("Ítem no encontrado")

    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        raise ValueError("El nombre es obligatorio")
    item.nombre = nombre
    db.session.commit()
    return _item_dict(item)


def baja_taxonomia_item(empresa_id: int, item_id: int) -> dict:
    item = TaxonomiaItem.query.filter_by(id=item_id, empresa_id=empresa_id, activo=True).first()
    if not item:
        raise ValueError("Ítem no encontrado")

    hijos = TaxonomiaItem.query.filter_by(parent_id=item.id, activo=True).count()
    if hijos:
        raise ValueError("No se puede eliminar: tiene ítems dependientes. Eliminá primero los hijos.")

    item.activo = False
    db.session.commit()
    return {"id": item.id, "activo": False}


def validar_clasificacion(
    empresa_id: int,
    categoria: str | None,
    tipo: str | None,
    origen: str | None,
    modalidad: str | None,
    *,
    requerido: bool = False,
) -> tuple[str | None, str | None, str | None, str | None]:
    categoria = (categoria or "").strip().lower() or None
    tipo = (tipo or "").strip().lower() or None
    origen = (origen or "").strip().lower() or None
    modalidad = (modalidad or "").strip().lower() or None

    if not any((categoria, tipo, origen, modalidad)):
        if requerido:
            raise ValueError("Debe completar Categoría, Tipo, Origen y Modalidad")
        return None, None, None, None

    if not categoria:
        if tipo or origen:
            raise ValueError("Debe indicar la categoría")
        return None, None, None, None

    arbol = arbol_taxonomia(empresa_id)
    if categoria not in arbol:
        raise ValueError("Categoría inválida")
    if not tipo or tipo not in arbol[categoria]["tipos"]:
        raise ValueError("Tipo inválido para la categoría seleccionada")
    origenes = arbol[categoria]["tipos"][tipo]["origenes"]
    if not origen or origen not in origenes:
        raise ValueError("Origen inválido para el tipo seleccionado")
    permitidas = origenes[origen]["modalidades"]
    if not modalidad or modalidad not in permitidas:
        raise ValueError("Modalidad inválida para el origen seleccionado")
    return categoria, tipo, origen, modalidad


def etiqueta_taxonomia(empresa_id: int, nivel: str, codigo: str | None) -> str | None:
    if not codigo:
        return None
    arbol = arbol_taxonomia(empresa_id)
    codigo = codigo.strip().lower()
    if nivel == "categoria":
        return arbol.get(codigo, {}).get("label", codigo.replace("_", " ").title())
    if nivel == "tipo":
        for cat in arbol.values():
            if codigo in cat.get("tipos", {}):
                return cat["tipos"][codigo]["label"]
    if nivel == "origen":
        for cat in arbol.values():
            for t in cat.get("tipos", {}).values():
                if codigo in t.get("origenes", {}):
                    return t["origenes"][codigo]["label"]
    if nivel == "modalidad":
        for cat in arbol.values():
            for t in cat.get("tipos", {}).values():
                for o in t.get("origenes", {}).values():
                    labels = o.get("modalidad_labels", {})
                    if codigo in labels:
                        return labels[codigo]
    return codigo.replace("_", " ").title()


def tipo_capacitacion_legacy(categoria: str | None, tipo: str | None) -> str | None:
    if not categoria:
        return None
    if tipo == "obligatoria" and categoria in ("hse", "sgi", "normativa", "induccion"):
        return categoria
    return categoria


def clasificacion_desde_legacy(
    empresa_id: int, tipo_capacitacion: str | None
) -> tuple[str | None, str | None, str | None]:
    from gos.modulos.capacitacion.models.taxonomia import (
        CASCADA_CAPACITACION,
        _LEGACY_TIPO_MAP,
    )

    if not tipo_capacitacion:
        return None, None, None
    key = tipo_capacitacion.strip().lower()
    mapped = _LEGACY_TIPO_MAP.get(key)
    if mapped:
        return mapped
    arbol = arbol_taxonomia(empresa_id)
    if key in arbol:
        tipos = arbol[key].get("tipos", {})
        tipo_codigo = next(iter(tipos), None)
        if not tipo_codigo:
            return key, None, None
        origenes = tipos[tipo_codigo].get("origenes", {})
        origen_codigo = next(iter(origenes), None)
        return key, tipo_codigo, origen_codigo
    if key in CASCADA_CAPACITACION:
        return key, "obligatoria", "interna"
    return None, None, None


def _item_dict(item: TaxonomiaItem) -> dict:
    return {
        "id": item.id,
        "nivel": item.nivel,
        "parent_id": item.parent_id,
        "codigo": item.codigo,
        "nombre": item.nombre,
        "orden": item.orden,
    }
