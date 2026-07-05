"""Matriz Analítica: calendario, tabla por plan y vista por persona."""

from __future__ import annotations

from datetime import date

from gos.modulos.capacitacion.models import (
    Acreditacion,
    EncuentroCapacitacion,
    Participante,
    PlanCurso,
    ProgramaCapacitacion,
    ProgramaPlan,
    ProgramaPuesto,
)
from gos.modulos.capacitacion.services.acreditacion_service import refrescar_vigencias

PLAN_COLORES = {
    "seguridad": "azul",
    "liderazgo": "verde",
    "tecnico": "ambar",
    "técnico": "ambar",
    "regulatorio": "purpura",
    "induccion": "verde_claro",
    "inducción": "verde_claro",
}


def _parse_ids(raw) -> list[int]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [int(x) for x in raw.split(",") if str(x).strip().isdigit()]
    return [int(x) for x in raw if x is not None and str(x).strip() != ""]


def _programas_filtrados(
    empresa_id: int,
    *,
    plan_ids: list[int],
    tipos: list[str],
    puesto_ids: list[int],
) -> list[ProgramaCapacitacion]:
    q = ProgramaCapacitacion.query.filter_by(empresa_id=empresa_id, activo=True)
    if tipos:
        q = q.filter(ProgramaCapacitacion.tipo.in_([t.lower() for t in tipos]))
    programas = q.order_by(ProgramaCapacitacion.nombre).all()
    if puesto_ids:
        permitidos = {
            pp.programa_id
            for pp in ProgramaPuesto.query.filter(ProgramaPuesto.puesto_id.in_(puesto_ids)).all()
        }
        programas = [
            p for p in programas if p.id in permitidos or (p.puesto_id and p.puesto_id in puesto_ids)
        ]
    if plan_ids:
        programas = [
            p
            for p in programas
            if any(pl.id in plan_ids for pl in p.planes.all())
        ]
    return programas


def _personas_filtradas(
    empresa_id: int,
    *,
    persona_ids: list[int],
    puesto_ids: list[int],
) -> list[Participante]:
    q = Participante.query.filter_by(empresa_id=empresa_id, activo=True)
    if persona_ids:
        q = q.filter(Participante.id.in_(persona_ids))
    if puesto_ids:
        q = q.filter(Participante.puesto_id.in_(puesto_ids))
    return q.order_by(Participante.apellido, Participante.nombre).all()


def _progreso_color(porcentaje: float) -> str:
    if porcentaje >= 100:
        return "verde"
    if porcentaje >= 50:
        return "ambar"
    return "rojo"


def _estado_acreditacion(acr: Acreditacion | None, hoy: date) -> str:
    """Estado visible: cursos vencidos figuran como pendientes."""
    if not acr or not acr.aprobo:
        return "pendiente" if not acr or acr.aprobo is None else "no_aprobo"
    if acr.fecha_vencimiento and acr.fecha_vencimiento < hoy:
        return "pendiente"
    if not acr.vigente:
        return "pendiente"
    return "aprobada"


def _asistio_desde_acreditacion(acr: Acreditacion | None) -> bool | None:
    if not acr or not acr.cronograma_persona:
        return None
    asist = acr.cronograma_persona.asistencia
    if asist == "presente":
        return True
    if asist == "ausente":
        return False
    return None


def _acr_coincide_empresa(acr: Acreditacion | None, empresas: list[int]) -> bool:
    if not empresas:
        return True
    if not acr or not acr.cronograma_persona or not acr.cronograma_persona.encuentro:
        return False
    enc = acr.cronograma_persona.encuentro
    return enc.empresa_capacitadora_id in empresas


def _badge_origen(curso, empresa_nombre: str | None = None) -> str:
    if (curso.origen or "").startswith("extern"):
        return empresa_nombre or "Empresa externa"
    return "GOS Interno"


def _empresa_dictada_por_acreditacion(acr: Acreditacion | None) -> str | None:
    if not acr or not acr.cronograma_persona_id:
        return None
    asist = acr.cronograma_persona
    if not asist or not asist.encuentro:
        return None
    enc = asist.encuentro
    if enc.empresa_capacitadora:
        return enc.empresa_capacitadora.nombre
    if (enc.origen or "").startswith("extern"):
        return "Empresa externa"
    return "GOS Interno"


def matriz_filtros_metadata(empresa_id: int) -> dict:
    from gos.modulos.capacitacion.models import EmpresaCapacitadora, Puesto

    personas = Participante.query.filter_by(empresa_id=empresa_id, activo=True).order_by(
        Participante.apellido, Participante.nombre
    ).all()
    puestos = Puesto.query.filter_by(empresa_id=empresa_id, activo=True).order_by(Puesto.nombre).all()
    empresas = EmpresaCapacitadora.query.filter_by(empresa_id=empresa_id, activo=True).order_by(
        EmpresaCapacitadora.nombre
    ).all()
    return {
        "planes": listar_planes_filtro(empresa_id),
        "tipos": [{"id": "interno", "nombre": "Interno"}, {"id": "externo", "nombre": "Externo"}],
        "empresas": [{"id": e.id, "nombre": e.nombre} for e in empresas],
        "personas": [
            {"id": p.id, "nombre": p.nombre_completo, "legajo": p.legajo, "puesto_id": p.puesto_id}
            for p in personas
        ],
        "puestos": [{"id": p.id, "nombre": p.nombre} for p in puestos],
    }


def listar_planes_filtro(empresa_id: int) -> list[dict]:
    planes = (
        ProgramaPlan.query.join(ProgramaCapacitacion)
        .filter(ProgramaCapacitacion.empresa_id == empresa_id, ProgramaCapacitacion.activo.is_(True))
        .order_by(ProgramaPlan.nombre)
        .all()
    )
    vistos = {}
    for pl in planes:
        key = pl.nombre.strip().lower()
        if key not in vistos:
            vistos[key] = {
                "id": pl.id,
                "nombre": pl.nombre,
                "color": PLAN_COLORES.get(key, "azul"),
                "ids": [pl.id],
            }
        else:
            vistos[key]["ids"].append(pl.id)
    return list(vistos.values())


def matriz_calendario(
    empresa_id: int,
    *,
    anio: int | None = None,
    plan_ids: list[int] | None = None,
    tipos: list[str] | None = None,
    empresas: list[int] | None = None,
    persona_ids: list[int] | None = None,
    puesto_ids: list[int] | None = None,
) -> dict:
    anio = anio or date.today().year
    plan_ids = plan_ids or []
    tipos = tipos or []
    empresas = empresas or []
    persona_ids = persona_ids or []
    puesto_ids = puesto_ids or []

    programas = _programas_filtrados(empresa_id, plan_ids=plan_ids, tipos=tipos, puesto_ids=puesto_ids)
    programa_ids = {p.id for p in programas}
    plan_ids_validos = set()
    for p in programas:
        for pl in p.planes.all():
            if not plan_ids or pl.id in plan_ids:
                plan_ids_validos.add(pl.id)

    q = EncuentroCapacitacion.query.filter_by(empresa_id=empresa_id).filter(
        EncuentroCapacitacion.fecha >= date(anio, 1, 1),
        EncuentroCapacitacion.fecha <= date(anio, 12, 31),
    )
    if tipos:
        origenes = []
        if "interno" in tipos:
            origenes.extend(["interna", "interno", None])
        if "externo" in tipos:
            origenes.extend(["externa", "externo"])
        # filtrar en Python por flexibilidad con null
    encuentros = q.order_by(EncuentroCapacitacion.fecha).all()

    meses: dict[int, list] = {m: [] for m in range(1, 13)}
    for enc in encuentros:
        # Sin fecha_inicio explícita: planificado pero aún no calendarizado
        if enc.fecha_inicio is None:
            continue
        if tipos:
            tipo_enc = "externo" if (enc.origen or "").startswith("extern") else "interno"
            if tipo_enc not in tipos:
                continue
        if empresas and enc.empresa_capacitadora_id not in empresas:
            continue
        if plan_ids_validos and enc.plan_id and enc.plan_id not in plan_ids_validos:
            continue
        if programa_ids and enc.programa_id and enc.programa_id not in programa_ids:
            # permitir encuentros sin programa si no hay filtro de plan
            if plan_ids:
                continue

        personas = [
            {
                "id": a.participante_id,
                "nombre": a.participante.nombre_completo if a.participante else None,
                "asistio": a.asistencia == "presente",
                "nota": float(a.nota) if a.nota is not None else None,
                "aprobo": a.aprobado,
            }
            for a in enc.asistencias.all()
            if a.participante and a.participante.activo
        ]
        if persona_ids:
            personas = [p for p in personas if p["id"] in persona_ids]
            if not personas:
                continue
        if puesto_ids:
            personas = [
                p
                for p in personas
                if any(
                    part.id == p["id"] and part.puesto_id in puesto_ids
                    for part in (a.participante for a in enc.asistencias.all())
                )
            ]
            if not personas and enc.asistencias.count():
                continue

        plan_nombre = enc.plan.nombre if enc.plan else None
        color = PLAN_COLORES.get((plan_nombre or "").lower(), "azul")
        meses[enc.fecha.month].append(
            {
                "id": enc.id,
                "curso_nombre": enc.curso.nombre if enc.curso else enc.titulo,
                "fecha": enc.fecha.isoformat(),
                "fecha_inicio": enc.fecha_inicio.isoformat() if enc.fecha_inicio else None,
                "fecha_fin": enc.fecha_fin.isoformat() if enc.fecha_fin else None,
                "empresa_nombre": enc.empresa_capacitadora.nombre if enc.empresa_capacitadora else None,
                "tipo": "externo" if (enc.origen or "").startswith("extern") else "interno",
                "plan_nombre": plan_nombre,
                "color": color,
                "estado": enc.estado,
                "personas_count": len(personas) or enc.asistencias.count(),
                "personas": personas,
                "capacitador": enc.instructor,
                "lugar": enc.lugar,
                "link": enc.link_virtual,
            }
        )

    return {"anio": anio, "meses": meses}


def matriz_tabla(
    empresa_id: int,
    *,
    plan_ids: list[int] | None = None,
    tipos: list[str] | None = None,
    empresas: list[int] | None = None,
    persona_ids: list[int] | None = None,
    puesto_ids: list[int] | None = None,
) -> dict:
    refrescar_vigencias(empresa_id)
    plan_ids = plan_ids or []
    tipos = tipos or []
    persona_ids = persona_ids or []
    puesto_ids = puesto_ids or []
    empresas = empresas or []

    programas = _programas_filtrados(empresa_id, plan_ids=plan_ids, tipos=tipos, puesto_ids=puesto_ids)
    personas = _personas_filtradas(empresa_id, persona_ids=persona_ids, puesto_ids=puesto_ids)
    hoy = date.today()

    secciones = []
    for programa in programas:
        for plan in programa.planes.order_by(ProgramaPlan.orden).all():
            if plan_ids and plan.id not in plan_ids:
                continue
            cursos_sec = []
            for pc in plan.cursos.order_by(PlanCurso.orden).all():
                curso = pc.curso
                if not curso or not curso.activo:
                    continue
                filas = []
                horas_req = float(curso.horas or 0)
                horas_ok = 0.0
                for persona in personas:
                    if persona.puesto_id and not any(
                        pp.puesto_id == persona.puesto_id for pp in programa.puestos_asignados.all()
                    ):
                        if programa.puesto_id != persona.puesto_id:
                            continue
                    acr = Acreditacion.query.filter_by(
                        persona_id=persona.id,
                        programa_id=programa.id,
                        plan_id=plan.id,
                        curso_id=curso.id,
                    ).first()
                    if empresas and not _acr_coincide_empresa(acr, empresas):
                        continue
                    estado = _estado_acreditacion(acr, hoy)
                    if estado == "aprobada":
                        horas_ok += float(acr.horas_acreditadas or curso.horas or 0)
                    filas.append(
                        {
                            "persona_id": persona.id,
                            "persona": persona.nombre_completo,
                            "puesto": persona.puesto.nombre if persona.puesto else None,
                            "asistio": _asistio_desde_acreditacion(acr),
                            "nota": float(acr.nota) if acr and acr.nota is not None else None,
                            "estado": estado,
                            "horas_acreditadas": float(acr.horas_acreditadas)
                            if acr and acr.horas_acreditadas is not None and estado == "aprobada"
                            else 0,
                            "fecha_vencimiento": acr.fecha_vencimiento.isoformat()
                            if acr and acr.fecha_vencimiento
                            else None,
                        }
                    )
                if empresas and not filas:
                    continue
                total_req = horas_req * max(len(filas), 1)
                pct = round((horas_ok / total_req) * 100, 1) if total_req else 0
                cursos_sec.append(
                    {
                        "curso_id": curso.id,
                        "curso_nombre": curso.nombre,
                        "horas": horas_req,
                        "origen_badge": _badge_origen(curso),
                        "tiene_vigencia": curso.tiene_vigencia,
                        "meses_vigencia": curso.vigencia_meses,
                        "personas": filas,
                        "progreso": {
                            "horas_acreditadas": horas_ok,
                            "horas_requeridas": total_req,
                            "porcentaje": pct,
                            "color": _progreso_color(pct),
                        },
                    }
                )
            if cursos_sec:
                secciones.append(
                    {
                        "programa_id": programa.id,
                        "programa_nombre": programa.nombre,
                        "programa_tipo": programa.tipo,
                        "plan_id": plan.id,
                        "plan_nombre": plan.nombre,
                        "color": PLAN_COLORES.get(plan.nombre.lower(), "azul"),
                        "cursos": cursos_sec,
                    }
                )
    return {"secciones": secciones, "hoy": hoy.isoformat()}


def matriz_persona(
    empresa_id: int,
    persona_id: int,
    *,
    plan_ids: list[int] | None = None,
    tipos: list[str] | None = None,
    empresas: list[int] | None = None,
) -> dict:
    refrescar_vigencias(empresa_id)
    persona = Participante.query.filter_by(id=persona_id, empresa_id=empresa_id, activo=True).first()
    if not persona:
        raise ValueError("Persona no encontrada")

    plan_ids = plan_ids or []
    tipos = tipos or []
    programas = _programas_filtrados(
        empresa_id,
        plan_ids=plan_ids,
        tipos=tipos,
        puesto_ids=[persona.puesto_id] if persona.puesto_id else [],
    )

    hoy = date.today()
    horas_ok = 0.0
    horas_req = 0.0
    materias_ok = 0
    materias_tot = 0
    cards = []

    for programa in programas:
        cursos_card = []
        pendientes = []
        p_ok = 0.0
        p_req = 0.0
        m_ok = 0
        m_tot = 0
        for plan in programa.planes.order_by(ProgramaPlan.orden).all():
            if plan_ids and plan.id not in plan_ids:
                continue
            for pc in plan.cursos.order_by(PlanCurso.orden).all():
                curso = pc.curso
                if not curso or not curso.activo:
                    continue
                hs = float(curso.horas or 0)
                m_tot += 1
                p_req += hs
                acr = Acreditacion.query.filter_by(
                    persona_id=persona.id,
                    programa_id=programa.id,
                    plan_id=plan.id,
                    curso_id=curso.id,
                ).first()
                estado = _estado_acreditacion(acr, hoy)
                if estado == "aprobada":
                    m_ok += 1
                    p_ok += float(acr.horas_acreditadas or hs)
                else:
                    pendientes.append(curso.nombre)
                empresa_dictada = _empresa_dictada_por_acreditacion(acr) or _badge_origen(curso)
                if empresas and not _acr_coincide_empresa(acr, empresas):
                    continue
                cursos_card.append(
                    {
                        "curso": curso.nombre,
                        "hs": hs,
                        "nota": float(acr.nota) if acr and acr.nota is not None else None,
                        "estado": estado,
                        "empresa": empresa_dictada,
                        "plan_nombre": plan.nombre,
                    }
                )
        horas_ok += p_ok
        horas_req += p_req
        materias_ok += m_ok
        materias_tot += m_tot
        if cursos_card:
            cards.append(
                {
                    "programa_id": programa.id,
                    "programa_nombre": programa.nombre,
                    "tipo": programa.tipo,
                    "progreso": {
                        "horas_completadas": p_ok,
                        "horas_requeridas": p_req,
                        "materias_ok": m_ok,
                        "materias_tot": m_tot,
                        "porcentaje": round((p_ok / p_req) * 100, 1) if p_req else 0,
                    },
                    "cursos": cursos_card,
                    "pendientes": pendientes,
                }
            )

    return {
        "persona": {
            "id": persona.id,
            "nombre": persona.nombre_completo,
            "puesto": persona.puesto.nombre if persona.puesto else None,
            "tiene_foto": bool(persona.foto_path),
        },
        "metricas": {
            "horas_completadas": horas_ok,
            "horas_requeridas": horas_req,
            "porcentaje": round((horas_ok / horas_req) * 100, 1) if horas_req else 0,
            "materias_aprobadas": materias_ok,
            "materias_totales": materias_tot,
        },
        "programas": cards,
        "hoy": hoy.isoformat(),
    }


def matriz_analitica(
    empresa_id: int,
    *,
    vista: str = "tabla",
    anio: int | None = None,
    plan_ids=None,
    tipos=None,
    empresas=None,
    persona_ids=None,
    puesto_ids=None,
    persona_id: int | None = None,
) -> dict:
    plan_ids = _parse_ids(plan_ids)
    tipos = [t.lower() for t in (tipos or []) if t]
    empresas = _parse_ids(empresas)
    persona_ids = _parse_ids(persona_ids)
    puesto_ids = _parse_ids(puesto_ids)

    filtros = matriz_filtros_metadata(empresa_id)

    if vista == "calendar" or vista == "calendario":
        data = matriz_calendario(
            empresa_id,
            anio=anio,
            plan_ids=plan_ids,
            tipos=tipos,
            empresas=empresas,
            persona_ids=persona_ids,
            puesto_ids=puesto_ids,
        )
    elif vista == "person" or vista == "persona":
        pid = persona_id or (persona_ids[0] if persona_ids else None)
        if not pid:
            raise ValueError("Seleccioná una persona para la vista por persona")
        data = matriz_persona(
            empresa_id,
            pid,
            plan_ids=plan_ids,
            tipos=tipos,
            empresas=empresas,
        )
    else:
        data = matriz_tabla(
            empresa_id,
            plan_ids=plan_ids,
            tipos=tipos,
            empresas=empresas,
            persona_ids=persona_ids,
            puesto_ids=puesto_ids,
        )

    return {"vista": vista, "filtros": filtros, "data": data}
