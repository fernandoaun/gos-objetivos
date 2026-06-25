"""Búsqueda global en participantes, cursos y programas."""

from __future__ import annotations

from gos.modulos.capacitacion.models import Curso, Participante, ProgramaCapacitacion


def busqueda_global(empresa_id: int, q: str, *, limit: int = 20) -> dict:
    term = (q or "").strip().lower()
    if len(term) < 2:
        return {"resultados": []}

    resultados: list[dict] = []

    participantes = (
        Participante.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(Participante.nombre)
        .all()
    )
    for p in participantes:
        hay = (
            term in p.nombre_completo.lower()
            or term in (p.legajo or "").lower()
            or term in (p.dni or "").lower()
            or term in (p.email or "").lower()
        )
        if hay:
            resultados.append(
                {
                    "tipo": "participante",
                    "id": p.id,
                    "titulo": p.nombre_completo,
                    "subtitulo": p.legajo or p.sector.nombre if p.sector else "",
                    "vista": "personas",
                }
            )
        if len(resultados) >= limit:
            return {"resultados": resultados}

    cursos = Curso.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Curso.nombre).all()
    for c in cursos:
        if term in c.nombre.lower() or term in c.codigo.lower():
            resultados.append(
                {
                    "tipo": "curso",
                    "id": c.id,
                    "titulo": f"{c.codigo} — {c.nombre}",
                    "subtitulo": c.tipo_capacitacion or "",
                    "vista": "catalogos",
                }
            )
        if len(resultados) >= limit:
            return {"resultados": resultados}

    programas = (
        ProgramaCapacitacion.query.filter_by(empresa_id=empresa_id)
        .order_by(ProgramaCapacitacion.nombre)
        .all()
    )
    for pr in programas:
        if term in pr.nombre.lower() or term in pr.codigo.lower():
            resultados.append(
                {
                    "tipo": "programa",
                    "id": pr.id,
                    "titulo": f"{pr.codigo} — {pr.nombre}",
                    "subtitulo": pr.estado or "",
                    "vista": "programas",
                }
            )
        if len(resultados) >= limit:
            break

    return {"resultados": resultados[:limit]}
