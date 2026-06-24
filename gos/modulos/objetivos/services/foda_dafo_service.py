"""Matriz DAFO 2×2: una sola tarea editable por cuadrante (FO, FA, DO, DA)."""
from __future__ import annotations

from dataclasses import dataclass

from gos.extensions import db
from gos.modulos.objetivos.models.foda import FODA_LABELS, FODA_TIPOS, DafoTarea, FodaItem

DAFO_TIPOS = ("FO", "DO", "FA", "DA")

# Marcador en BD para la tarea única del cuadrante (no cruces ítem a ítem).
CELDA_MATRIZ = "*"

DAFO_META = {
    "FO": {
        "titulo": "FO",
        "subtitulo": "Fortalezas × Oportunidades",
        "enfoque": "Ofensivas · Maximizar",
        "icono": "bi-rocket-takeoff",
        "css": "fo",
    },
    "DO": {
        "titulo": "DO",
        "subtitulo": "Debilidades × Oportunidades",
        "enfoque": "Conversión · Reorientar",
        "icono": "bi-arrow-repeat",
        "css": "do",
    },
    "FA": {
        "titulo": "FA",
        "subtitulo": "Fortalezas × Amenazas",
        "enfoque": "Defensivas · Proteger",
        "icono": "bi-shield-fill-check",
        "css": "fa",
    },
    "DA": {
        "titulo": "DA",
        "subtitulo": "Debilidades × Amenazas",
        "enfoque": "Supervivencia · Mitigar",
        "icono": "bi-exclamation-octagon",
        "css": "da",
    },
}

_CRUCES = {
    "FO": ("F", "O"),
    "DO": ("D", "O"),
    "FA": ("F", "A"),
    "DA": ("D", "A"),
}


@dataclass(frozen=True)
class CuadranteDafo:
    id: int | None
    tipo: str
    tarea: str
    activo: bool
    resumen_a: str
    resumen_b: str


def _orden_item(item: FodaItem) -> tuple:
    return (getattr(item, "orden", 0) or 0, getattr(item, "id", 0) or 0)


def _resumen_items(items: list[FodaItem], max_items: int = 5) -> str:
    if not items:
        return ""
    ordenados = sorted(items, key=_orden_item)[:max_items]
    partes = [f"{it.codigo}: {it.descripcion}" for it in ordenados]
    if len(items) > max_items:
        partes.append(f"(+{len(items) - max_items} más)")
    return " · ".join(partes)


def _texto_plantilla_legacy(tipo: str, matriz: dict[str, list[FodaItem]]) -> str:
    """Texto autogenerado antiguo (listaba ítems duplicados respecto al resumen)."""
    tipo_a, tipo_b = _CRUCES[tipo]
    items_a = matriz.get(tipo_a, [])
    items_b = matriz.get(tipo_b, [])
    if not items_a or not items_b:
        return ""
    res_a = _resumen_items(items_a)
    res_b = _resumen_items(items_b)
    return (
        f"Tarea {tipo} — {FODA_LABELS[tipo_a]} × {FODA_LABELS[tipo_b]}:\n"
        f"Con {FODA_LABELS[tipo_a].lower()}: {res_a}\n"
        f"Y {FODA_LABELS[tipo_b].lower()}: {res_b}\n"
        f"Definir la acción estratégica principal para este cruce."
    )


def _texto_inicial_cuadrante(tipo: str, matriz: dict[str, list[FodaItem]]) -> str | None:
    tipo_a, tipo_b = _CRUCES[tipo]
    items_a = matriz.get(tipo_a, [])
    items_b = matriz.get(tipo_b, [])
    if not items_a or not items_b:
        return None
    return ""


def _normalizar_tarea(tarea: str, tipo: str, matriz: dict[str, list[FodaItem]]) -> str:
    if not tarea.strip():
        return ""
    if tarea.strip() == _texto_plantilla_legacy(tipo, matriz).strip():
        return ""
    return tarea


def _limpiar_tareas_granulares(empresa_id: int) -> None:
    """Elimina tareas viejas ítem×ítem; la matriz usa una tarea por cuadrante."""
    DafoTarea.query.filter(
        DafoTarea.empresa_id == empresa_id,
        DafoTarea.origen_a_codigo != CELDA_MATRIZ,
    ).delete(synchronize_session=False)


def _obtener_o_crear_cuadrante_db(
    empresa_id: int,
    tipo: str,
    matriz: dict[str, list[FodaItem]],
) -> CuadranteDafo:
    tipo_a, tipo_b = _CRUCES[tipo]
    items_a = matriz.get(tipo_a, [])
    items_b = matriz.get(tipo_b, [])
    activo = bool(items_a and items_b)
    default = _texto_inicial_cuadrante(tipo, matriz) or ""

    row = DafoTarea.query.filter_by(
        empresa_id=empresa_id,
        tipo=tipo,
        origen_a_codigo=CELDA_MATRIZ,
        origen_b_codigo=CELDA_MATRIZ,
    ).first()
    if not row and activo:
        row = DafoTarea(
            empresa_id=empresa_id,
            tipo=tipo,
            origen_a_codigo=CELDA_MATRIZ,
            origen_b_codigo=CELDA_MATRIZ,
            tarea=default,
        )
        db.session.add(row)
        db.session.flush()

    tarea = _normalizar_tarea(row.tarea if row else "", tipo, matriz)
    if row and row.tarea != tarea:
        row.tarea = tarea

    return CuadranteDafo(
        id=row.id if row else None,
        tipo=tipo,
        tarea=tarea,
        activo=activo,
        resumen_a=_resumen_items(items_a),
        resumen_b=_resumen_items(items_b),
    )


def _cuadrante_sin_db(tipo: str, matriz: dict[str, list[FodaItem]]) -> CuadranteDafo:
    tipo_a, tipo_b = _CRUCES[tipo]
    items_a = matriz.get(tipo_a, [])
    items_b = matriz.get(tipo_b, [])
    activo = bool(items_a and items_b)
    return CuadranteDafo(
        id=None,
        tipo=tipo,
        tarea=_normalizar_tarea(_texto_inicial_cuadrante(tipo, matriz) or "", tipo, matriz),
        activo=activo,
        resumen_a=_resumen_items(items_a),
        resumen_b=_resumen_items(items_b),
    )


def generar_matriz_dafo(
    matriz: dict[str, list[FodaItem]],
    empresa_id: int | None = None,
) -> dict[str, dict]:
    resultado: dict[str, dict] = {}
    if empresa_id is not None:
        _limpiar_tareas_granulares(empresa_id)

    for tipo in DAFO_TIPOS:
        if empresa_id is not None:
            cuad = _obtener_o_crear_cuadrante_db(empresa_id, tipo, matriz)
        else:
            cuad = _cuadrante_sin_db(tipo, matriz)
        resultado[tipo] = {
            "cuadrante": cuad,
            "activo": cuad.activo,
            **DAFO_META[tipo],
        }

    if empresa_id is not None:
        db.session.commit()
    return resultado


def guardar_tarea_cuadrante(empresa_id: int, tipo: str, tarea: str) -> DafoTarea:
    if tipo not in DAFO_TIPOS:
        raise ValueError("Tipo DAFO inválido.")
    texto = (tarea or "").strip()
    if len(texto) < 3:
        raise ValueError("La tarea debe tener al menos 3 caracteres.")

    row = DafoTarea.query.filter_by(
        empresa_id=empresa_id,
        tipo=tipo,
        origen_a_codigo=CELDA_MATRIZ,
        origen_b_codigo=CELDA_MATRIZ,
    ).first()
    if not row:
        raise ValueError("Cuadrante DAFO no encontrado. Recargá la página FODA.")
    row.tarea = texto
    db.session.commit()
    return row


def total_cuadrantes_dafo(dafo: dict[str, dict]) -> int:
    return sum(1 for q in dafo.values() if q.get("activo"))


# Compatibilidad con rutas/tests previos
def guardar_tarea_celda(
    empresa_id: int,
    tipo: str,
    origen_a_codigo: str,
    origen_b_codigo: str,
    tarea: str,
) -> DafoTarea:
    return guardar_tarea_cuadrante(empresa_id, tipo, tarea)


def total_estrategias_dafo(dafo: dict[str, dict]) -> int:
    return total_cuadrantes_dafo(dafo)
