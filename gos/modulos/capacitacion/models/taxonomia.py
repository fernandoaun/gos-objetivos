"""Taxonomía en cascada para cursos: Categoría → Tipo → Origen → Modalidad."""

from __future__ import annotations

MODALIDADES = ("presencial", "virtual", "mixta")

_MODALIDAD_LABELS = {
    "presencial": "Presencial",
    "virtual": "Virtual",
    "mixta": "Mixta",
}

CASCADA_CAPACITACION: dict[str, dict] = {
    "hse": {
        "label": "HSE",
        "tipos": {
            "obligatoria": {
                "label": "Obligatoria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual"),
                    },
                },
            },
            "complementaria": {
                "label": "Complementaria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                },
            },
        },
    },
    "sgi": {
        "label": "SGI",
        "tipos": {
            "obligatoria": {
                "label": "Obligatoria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual"),
                    },
                },
            },
            "complementaria": {
                "label": "Complementaria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                },
            },
        },
    },
    "tecnica": {
        "label": "Técnica",
        "tipos": {
            "obligatoria": {
                "label": "Obligatoria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual"),
                    },
                },
            },
            "complementaria": {
                "label": "Complementaria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                },
            },
        },
    },
    "normativa": {
        "label": "Normativa",
        "tipos": {
            "obligatoria": {
                "label": "Obligatoria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual"),
                    },
                },
            },
            "complementaria": {
                "label": "Complementaria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                },
            },
        },
    },
    "induccion": {
        "label": "Inducción",
        "tipos": {
            "obligatoria": {
                "label": "Obligatoria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                },
            },
        },
    },
    "desarrollo": {
        "label": "Desarrollo",
        "tipos": {
            "complementaria": {
                "label": "Complementaria",
                "origenes": {
                    "interna": {
                        "label": "Interna",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual", "mixta"),
                    },
                },
            },
            "certificacion": {
                "label": "Certificación",
                "origenes": {
                    "externa": {
                        "label": "Externa",
                        "modalidades": ("presencial", "virtual"),
                    },
                },
            },
        },
    },
}

# Compatibilidad con imports y datos históricos
TIPOS_CAPACITACION = tuple(CASCADA_CAPACITACION.keys()) + (
    "obligatoria",
    "interna",
    "externa",
)

# Mapeo del campo legado tipo_capacitacion → (categoria, tipo, origen)
_LEGACY_TIPO_MAP: dict[str, tuple[str, str, str]] = {
    "hse": ("hse", "obligatoria", "interna"),
    "sgi": ("sgi", "obligatoria", "interna"),
    "tecnica": ("tecnica", "complementaria", "interna"),
    "normativa": ("normativa", "obligatoria", "interna"),
    "induccion": ("induccion", "obligatoria", "interna"),
    "interna": ("tecnica", "complementaria", "interna"),
    "externa": ("tecnica", "complementaria", "externa"),
    "obligatoria": ("tecnica", "obligatoria", "interna"),
}


def taxonomia_arbol() -> dict:
    """Árbol completo para el frontend (cascada)."""
    return CASCADA_CAPACITACION


def etiqueta_modalidad(modalidad: str | None) -> str | None:
    if not modalidad:
        return None
    return _MODALIDAD_LABELS.get(modalidad, modalidad.replace("_", " ").title())


def etiqueta_nivel(nivel: str, clave: str | None) -> str | None:
    if not clave:
        return None
    if nivel == "modalidad":
        return etiqueta_modalidad(clave)
    if nivel == "categoria":
        return CASCADA_CAPACITACION.get(clave, {}).get("label", clave.replace("_", " ").title())
    if nivel == "tipo" and clave:
        for cat in CASCADA_CAPACITACION.values():
            if clave in cat.get("tipos", {}):
                return cat["tipos"][clave]["label"]
    if nivel == "origen" and clave:
        for cat in CASCADA_CAPACITACION.values():
            for tipo in cat.get("tipos", {}).values():
                if clave in tipo.get("origenes", {}):
                    return tipo["origenes"][clave]["label"]
    return clave.replace("_", " ").title()


def opciones_categorias() -> list[tuple[str, str]]:
    return [(k, v["label"]) for k, v in CASCADA_CAPACITACION.items()]


def opciones_tipos(categoria: str | None) -> list[tuple[str, str]]:
    if not categoria or categoria not in CASCADA_CAPACITACION:
        return []
    return [(k, v["label"]) for k, v in CASCADA_CAPACITACION[categoria]["tipos"].items()]


def opciones_origenes(categoria: str | None, tipo: str | None) -> list[tuple[str, str]]:
    if not categoria or not tipo:
        return []
    tipos = CASCADA_CAPACITACION.get(categoria, {}).get("tipos", {})
    if tipo not in tipos:
        return []
    return [(k, v["label"]) for k, v in tipos[tipo]["origenes"].items()]


def opciones_modalidades(
    categoria: str | None, tipo: str | None, origen: str | None
) -> list[tuple[str, str]]:
    if not categoria or not tipo or not origen:
        return []
    tipos = CASCADA_CAPACITACION.get(categoria, {}).get("tipos", {})
    origenes = tipos.get(tipo, {}).get("origenes", {})
    if origen not in origenes:
        return []
    return [(m, _MODALIDAD_LABELS[m]) for m in origenes[origen]["modalidades"]]


def validar_clasificacion(
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

    if categoria not in CASCADA_CAPACITACION:
        raise ValueError("Categoría inválida")
    if not tipo or tipo not in CASCADA_CAPACITACION[categoria]["tipos"]:
        raise ValueError("Tipo inválido para la categoría seleccionada")
    origenes = CASCADA_CAPACITACION[categoria]["tipos"][tipo]["origenes"]
    if not origen or origen not in origenes:
        raise ValueError("Origen inválido para el tipo seleccionado")
    permitidas = origenes[origen]["modalidades"]
    if not modalidad or modalidad not in permitidas:
        raise ValueError("Modalidad inválida para el origen seleccionado")
    return categoria, tipo, origen, modalidad


def clasificacion_desde_legacy(tipo_capacitacion: str | None) -> tuple[str | None, str | None, str | None]:
    if not tipo_capacitacion:
        return None, None, None
    key = tipo_capacitacion.strip().lower()
    mapped = _LEGACY_TIPO_MAP.get(key)
    if mapped:
        return mapped
    if key in CASCADA_CAPACITACION:
        return key, "obligatoria", "interna"
    return None, None, None


def tipo_capacitacion_legacy(categoria: str | None, tipo: str | None) -> str | None:
    """Compatibilidad con reportes que usaban tipo_capacitacion."""
    if not categoria:
        return None
    if tipo == "obligatoria" and categoria in ("hse", "sgi", "normativa", "induccion"):
        return categoria
    return categoria
