"""Detección de ítems de catálogo similares al texto ingresado."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from gos.modulos.capacitacion.models import Curso, EmpresaCapacitadora, Instructor, Puesto
from gos.modulos.capacitacion.models.taxonomia_item import TaxonomiaItem
from gos.modulos.objetivos.models.catalogos import Sector

TIPOS_SIMILITUD = frozenset(
    {"sector", "puesto", "instructor", "empresa_capacitadora", "taxonomia", "curso"}
)

TIPO_LABELS = {
    "sector": "Sector",
    "puesto": "Puesto",
    "instructor": "Capacitador",
    "empresa_capacitadora": "Empresa capacitadora",
    "taxonomia": "Taxonomía",
    "curso": "Curso",
}

NIVEL_TAXONOMIA_LABELS = {
    "categoria": "Categoría",
    "tipo": "Tipo",
    "origen": "Origen",
    "modalidad": "Modalidad",
}

_UMBRAL_SIMILITUD = 0.72


def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    s = unicodedata.normalize("NFKD", texto)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def _ratio_similitud(a: str, b: str) -> float:
    na, nb = normalizar_texto(a), normalizar_texto(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    base = SequenceMatcher(None, na, nb).ratio()
    if na in nb or nb in na:
        return max(base, 0.85)
    return base


def _puntaje_item(nombre: str, codigo: str | None, candidato: dict) -> float:
    score = _ratio_similitud(nombre, candidato.get("nombre") or "")
    if codigo and candidato.get("codigo"):
        score = max(score, _ratio_similitud(codigo, candidato["codigo"]))
    return score


def buscar_similares(
    empresa_id: int,
    tipo: str,
    nombre: str,
    *,
    codigo: str | None = None,
    nivel: str | None = None,
    exclude_id: int | None = None,
    limite: int = 5,
) -> list[dict]:
    tipo = (tipo or "").strip().lower()
    if tipo not in TIPOS_SIMILITUD:
        raise ValueError(f"Tipo inválido: {tipo}")

    nombre = (nombre or "").strip()
    codigo = (codigo or "").strip() or None
    if not nombre and not codigo:
        return []

    candidatos = _listar_candidatos(empresa_id, tipo, nivel)
    if exclude_id is not None:
        candidatos = [c for c in candidatos if c.get("id") != exclude_id]

    scored: list[tuple[float, dict]] = []
    for cand in candidatos:
        score = _puntaje_item(nombre or codigo or "", codigo, cand)
        if score >= _UMBRAL_SIMILITUD:
            entry = dict(cand)
            entry["similitud"] = round(score, 2)
            entry["tipo"] = tipo
            entry["tipo_label"] = _etiqueta_item(tipo, cand)
            scored.append((score, entry))

    scored.sort(key=lambda x: (-x[0], x[1].get("nombre") or ""))
    return [item for _, item in scored[:limite]]


def _etiqueta_item(tipo: str, item: dict) -> str:
    if tipo == "taxonomia":
        nivel = item.get("nivel") or ""
        return NIVEL_TAXONOMIA_LABELS.get(nivel, TIPO_LABELS[tipo])
    return TIPO_LABELS.get(tipo, tipo)


def _listar_candidatos(empresa_id: int, tipo: str, nivel: str | None) -> list[dict]:
    if tipo == "sector":
        rows = Sector.query.filter_by(empresa_id=empresa_id, activo=True).all()
        return [{"id": r.id, "codigo": r.codigo, "nombre": r.nombre} for r in rows]

    if tipo == "puesto":
        rows = Puesto.query.filter_by(empresa_id=empresa_id, activo=True).all()
        return [{"id": r.id, "codigo": r.codigo, "nombre": r.nombre} for r in rows]

    if tipo == "instructor":
        rows = Instructor.query.filter_by(empresa_id=empresa_id, activo=True).all()
        return [{"id": r.id, "codigo": r.codigo, "nombre": r.nombre} for r in rows]

    if tipo == "empresa_capacitadora":
        rows = EmpresaCapacitadora.query.filter_by(empresa_id=empresa_id, activo=True).all()
        return [{"id": r.id, "codigo": r.codigo, "nombre": r.nombre} for r in rows]

    if tipo == "curso":
        rows = Curso.query.filter_by(empresa_id=empresa_id, activo=True).all()
        return [{"id": r.id, "codigo": r.codigo, "nombre": r.nombre} for r in rows]

    if tipo == "taxonomia":
        nivel_norm = (nivel or "").strip().lower() or None
        q = TaxonomiaItem.query.filter_by(empresa_id=empresa_id, activo=True)
        if nivel_norm:
            q = q.filter_by(nivel=nivel_norm)
        rows = q.all()
        return [
            {"id": r.id, "codigo": r.codigo, "nombre": r.nombre, "nivel": r.nivel} for r in rows
        ]

    return []
