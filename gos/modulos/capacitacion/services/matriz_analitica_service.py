"""Matriz Analítica: calendario, tabla por plan y vista por persona."""

from __future__ import annotations

from calendar import monthrange
from datetime import date

from gos.modulos.capacitacion.models import (
    Acreditacion,
    AsistenciaEncuentro,
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

MESES_NOMBRES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

METRICAS_RESUMEN = (
    "programados",
    "pendientes",
    "cumplidos",
    "puntuales",
    "pend_vencidos",
)


def _metricas_vacias() -> dict:
    return {
        "programados": 0,
        "pendientes": 0,
        "cumplidos": 0,
        "pct_cumpl_prog": None,
        "puntuales": 0,
        "pct_punt_prog": None,
        "pend_vencidos": 0,
        "pct_venc_prog": None,
        "pend_sin_vencer": 0,
        "pend_vencidos_det": 0,
        "cumpl_puntuales": 0,
        "cumpl_no_puntuales": 0,
    }


def _metricas_cortas_vacias() -> dict:
    return {"prog": 0, "pdtes": 0, "cumpl": 0, "cumpl_prog": None}


def _ratio(num: int, den: int) -> float | None:
    if not den:
        return None
    return round(num / den, 4)


def _fin_de_mes(d: date) -> date:
    """Último día del mes de la fecha indicada (mes programado)."""
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def _sumar_metricas(dest: dict, src: dict) -> None:
    for k in (
        "programados",
        "pendientes",
        "cumplidos",
        "puntuales",
        "pend_vencidos",
        "pend_sin_vencer",
        "pend_vencidos_det",
        "cumpl_puntuales",
        "cumpl_no_puntuales",
    ):
        dest[k] += src.get(k, 0)


def _finalizar_metricas(m: dict) -> dict:
    prog = m["programados"]
    m["pct_cumpl_prog"] = _ratio(m["cumplidos"], prog)
    m["pct_punt_prog"] = _ratio(m["puntuales"], prog)
    m["pct_venc_prog"] = _ratio(m["pend_vencidos"], prog)
    m["pendientes"] = m["programados"] - m["cumplidos"]
    m["cumpl_no_puntuales"] = m["cumplidos"] - m["cumpl_puntuales"]
    m["pct_pend_sin_vencer"] = _ratio(m["pend_sin_vencer"], prog)
    m["pct_pend_vencidos"] = _ratio(m["pend_vencidos_det"], prog)
    m["pct_cumpl_puntuales"] = _ratio(m["cumpl_puntuales"], prog)
    m["pct_cumpl_no_puntuales"] = _ratio(m["cumpl_no_puntuales"], prog)
    return m


def _a_metricas_cortas(m: dict) -> dict:
    return {
        "prog": m["programados"],
        "pdtes": m["pendientes"],
        "cumpl": m["cumplidos"],
        "cumpl_prog": m["pct_cumpl_prog"],
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


def _encuentro_pasa_filtros(
    enc: EncuentroCapacitacion,
    *,
    tipos: list[str],
    empresas: list[int],
    plan_ids_validos: set[int],
    programa_ids: set[int],
    plan_ids: list[int],
) -> bool:
    if tipos:
        tipo_enc = "externo" if (enc.origen or "").startswith("extern") else "interno"
        if tipo_enc not in tipos:
            return False
    if empresas and enc.empresa_capacitadora_id not in empresas:
        return False
    if plan_ids_validos and enc.plan_id and enc.plan_id not in plan_ids_validos:
        return False
    if programa_ids and enc.programa_id and enc.programa_id not in programa_ids:
        if plan_ids:
            return False
    return True


def _acr_para_asistencia(
    asist: AsistenciaEncuentro,
    enc: EncuentroCapacitacion,
    cache: dict[int, Acreditacion | None],
) -> Acreditacion | None:
    if asist.id in cache:
        return cache[asist.id]
    acr = Acreditacion.query.filter_by(cronograma_persona_id=asist.id).first()
    if not acr and enc.curso_id and enc.programa_id and enc.plan_id:
        acr = Acreditacion.query.filter_by(
            persona_id=asist.participante_id,
            programa_id=enc.programa_id,
            plan_id=enc.plan_id,
            curso_id=enc.curso_id,
        ).first()
    cache[asist.id] = acr
    return acr


def _clasificar_asignacion(
    asist: AsistenciaEncuentro,
    enc: EncuentroCapacitacion,
    acr: Acreditacion | None,
    hoy: date,
) -> dict:
    cumplido = _estado_acreditacion(acr, hoy) == "aprobada" if acr else asist.aprobado is True
    fecha_aprob = None
    if acr and acr.fecha_aprobacion:
        fecha_aprob = acr.fecha_aprobacion
    elif asist.fecha_aprobacion:
        fecha_aprob = asist.fecha_aprobacion

    # El cumplimiento se compara contra el MES programado: se considera "puntual"
    # (a tiempo) si el curso se dictó dentro de ese mes o antes de fin de mes.
    puntual = False
    if cumplido and fecha_aprob and enc.fecha:
        puntual = fecha_aprob <= _fin_de_mes(enc.fecha)
    elif cumplido:
        puntual = True

    vencido = not cumplido and enc.fecha and _fin_de_mes(enc.fecha) < hoy

    return {
        "programados": 1,
        "cumplidos": 1 if cumplido else 0,
        "puntuales": 1 if cumplido and puntual else 0,
        "pend_vencidos": 1 if not cumplido and vencido else 0,
        "pend_sin_vencer": 1 if not cumplido and not vencido else 0,
        "pend_vencidos_det": 1 if not cumplido and vencido else 0,
        "cumpl_puntuales": 1 if cumplido and puntual else 0,
        "cumpl_no_puntuales": 1 if cumplido and not puntual else 0,
    }


def _asignacion_cuenta_metrica(delta: dict, metrica: str) -> bool:
    if metrica == "programados":
        return delta.get("programados", 0) > 0
    if metrica == "cumplidos":
        return delta.get("cumplidos", 0) > 0
    if metrica == "puntuales":
        return delta.get("puntuales", 0) > 0
    if metrica == "pend_vencidos":
        return delta.get("pend_vencidos", 0) > 0
    if metrica == "pendientes":
        return delta.get("programados", 0) > 0 and delta.get("cumplidos", 0) == 0
    return False


def _colectar_datos_anuales(
    empresa_id: int,
    *,
    anio: int,
    plan_ids: list[int],
    tipos: list[str],
    empresas: list[int],
    persona_ids: list[int],
    puesto_ids: list[int],
) -> dict:
    """Métricas agregadas y asignaciones individuales para drill-down."""
    refrescar_vigencias(empresa_id)
    hoy = date.today()

    programas = _programas_filtrados(empresa_id, plan_ids=plan_ids, tipos=tipos, puesto_ids=puesto_ids)
    programa_ids = {p.id for p in programas}
    plan_ids_validos: set[int] = set()
    plan_nombres: dict[int, str] = {}
    for p in programas:
        for pl in p.planes.all():
            if not plan_ids or pl.id in plan_ids:
                plan_ids_validos.add(pl.id)
                plan_nombres[pl.id] = pl.nombre

    filas = (
        AsistenciaEncuentro.query.join(EncuentroCapacitacion)
        .join(Participante)
        .filter(
            EncuentroCapacitacion.empresa_id == empresa_id,
            EncuentroCapacitacion.fecha >= date(anio, 1, 1),
            EncuentroCapacitacion.fecha <= date(anio, 12, 31),
            EncuentroCapacitacion.fecha_inicio.isnot(None),
            Participante.activo.is_(True),
        )
        .all()
    )

    acr_cache: dict[int, Acreditacion | None] = {}
    por_persona_mes: dict[int, dict[int, dict]] = {}
    por_puesto_mes: dict[int, dict[int, dict]] = {}
    por_plan_mes: dict[int, dict[int, dict]] = {}
    por_mes: dict[int, dict] = {m: _metricas_vacias() for m in range(1, 13)}
    nombres: dict[int, str] = {}
    puesto_nombres: dict[int, str] = {}
    asignaciones: list[dict] = []

    for asist in filas:
        enc = asist.encuentro
        persona = asist.participante
        if not enc or not persona:
            continue
        if persona_ids and persona.id not in persona_ids:
            continue
        if puesto_ids and persona.puesto_id not in puesto_ids:
            continue
        if not _encuentro_pasa_filtros(
            enc,
            tipos=tipos,
            empresas=empresas,
            plan_ids_validos=plan_ids_validos,
            programa_ids=programa_ids,
            plan_ids=plan_ids,
        ):
            continue

        mes = enc.fecha.month
        acr = _acr_para_asistencia(asist, enc, acr_cache)
        delta = _clasificar_asignacion(asist, enc, acr, hoy)
        plan_id = enc.plan_id or 0
        plan_nombre = plan_nombres.get(plan_id) or (enc.plan.nombre if enc.plan else "Sin plan")

        nombres[persona.id] = persona.nombre_completo
        puesto_id = persona.puesto_id or 0
        if persona.puesto:
            puesto_nombres[puesto_id] = persona.puesto.nombre
        elif puesto_id == 0:
            puesto_nombres.setdefault(0, "Sin puesto")
        if persona.id not in por_persona_mes:
            por_persona_mes[persona.id] = {m: _metricas_vacias() for m in range(1, 13)}
        if puesto_id not in por_puesto_mes:
            por_puesto_mes[puesto_id] = {m: _metricas_vacias() for m in range(1, 13)}
        if plan_id not in por_plan_mes:
            por_plan_mes[plan_id] = {m: _metricas_vacias() for m in range(1, 13)}
        _sumar_metricas(por_persona_mes[persona.id][mes], delta)
        _sumar_metricas(por_puesto_mes[puesto_id][mes], delta)
        _sumar_metricas(por_plan_mes[plan_id][mes], delta)
        _sumar_metricas(por_mes[mes], delta)

        curso = enc.curso
        emp_nombre = None
        if enc.empresa_capacitadora:
            emp_nombre = enc.empresa_capacitadora.nombre
        elif (enc.origen or "").startswith("extern"):
            emp_nombre = "Empresa externa"
        asignaciones.append(
            {
                "mes": mes,
                "plan_id": plan_id,
                "plan_nombre": plan_nombre,
                "persona_id": persona.id,
                "persona_nombre": persona.nombre_completo,
                "encuentro_id": enc.id,
                "curso_nombre": curso.nombre if curso else enc.titulo,
                "fecha": enc.fecha.isoformat() if enc.fecha else None,
                "fecha_realizacion": enc.fecha_realizacion.isoformat() if enc.fecha_realizacion else None,
                "capacitador": enc.instructor or (enc.instructor_rel.nombre if enc.instructor_rel else None),
                "lugar": enc.lugar,
                "link": enc.link_virtual,
                "empresa_nombre": emp_nombre,
                "delta": delta,
                "asistio": _asistio_desde_acreditacion(acr) if acr else (asist.asistencia == "presente"),
                "nota": float(acr.nota) if acr and acr.nota is not None else (float(asist.nota) if asist.nota is not None else None),
                "aprobo": acr.aprobo if acr else asist.aprobado,
            }
        )

    for mes in range(1, 13):
        _finalizar_metricas(por_mes[mes])
    for pid, meses in por_persona_mes.items():
        for mes in range(1, 13):
            _finalizar_metricas(meses[mes])
    for plid, meses in por_plan_mes.items():
        for mes in range(1, 13):
            _finalizar_metricas(meses[mes])
    for puid, meses in por_puesto_mes.items():
        for mes in range(1, 13):
            _finalizar_metricas(meses[mes])

    return {
        "por_mes": por_mes,
        "por_plan_mes": por_plan_mes,
        "por_persona_mes": por_persona_mes,
        "por_puesto_mes": por_puesto_mes,
        "nombres": nombres,
        "puesto_nombres": puesto_nombres,
        "plan_nombres": plan_nombres,
        "asignaciones": asignaciones,
    }


def _colectar_metricas_anuales(
    empresa_id: int,
    *,
    anio: int,
    plan_ids: list[int],
    tipos: list[str],
    empresas: list[int],
    persona_ids: list[int],
    puesto_ids: list[int],
) -> tuple[dict[int, dict[int, dict]], dict[int, dict], dict[int, str]]:
    """Métricas por (persona, mes) y agregado por mes."""
    datos = _colectar_datos_anuales(
        empresa_id,
        anio=anio,
        plan_ids=plan_ids,
        tipos=tipos,
        empresas=empresas,
        persona_ids=persona_ids,
        puesto_ids=puesto_ids,
    )
    return datos["por_persona_mes"], datos["por_mes"], datos["nombres"]


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

    _, por_mes, _ = _colectar_metricas_anuales(
        empresa_id,
        anio=anio,
        plan_ids=plan_ids,
        tipos=tipos,
        empresas=empresas,
        persona_ids=persona_ids,
        puesto_ids=puesto_ids,
    )

    filas = []
    totales = _metricas_vacias()
    for i, nombre in enumerate(MESES_NOMBRES, start=1):
        m = por_mes[i]
        filas.append({"mes": i, "nombre": nombre, **m})
        _sumar_metricas(totales, m)
    _finalizar_metricas(totales)

    return {"anio": anio, "filas": filas, "totales": totales}


def _fila_metricas(entity_id, nombre: str, metricas: dict) -> dict:
    return {"id": entity_id, "nombre": nombre, **metricas}


def matriz_resumen(
    empresa_id: int,
    *,
    anio: int | None = None,
    nivel: str = "programas",
    mes: int | None = None,
    plan_id: int | None = None,
    persona_id: int | None = None,
    metrica: str | None = None,
    plan_ids: list[int] | None = None,
    tipos: list[str] | None = None,
    empresas: list[int] | None = None,
    persona_ids: list[int] | None = None,
    puesto_ids: list[int] | None = None,
) -> dict:
    """Resumen mensual con drill-down: programas → planes → personas → detalle."""
    anio = anio or date.today().year
    plan_ids = plan_ids or []
    tipos = tipos or []
    empresas = empresas or []
    persona_ids = persona_ids or []
    puesto_ids = puesto_ids or []
    nivel = (nivel or "programas").lower()

    datos = _colectar_datos_anuales(
        empresa_id,
        anio=anio,
        plan_ids=plan_ids,
        tipos=tipos,
        empresas=empresas,
        persona_ids=persona_ids,
        puesto_ids=puesto_ids,
    )

    if nivel == "detalle":
        if not mes:
            raise ValueError("Seleccioná un mes para ver el detalle")
        eventos_map: dict[int, dict] = {}
        for a in datos["asignaciones"]:
            if a["mes"] != mes:
                continue
            if plan_id and a["plan_id"] != plan_id:
                continue
            if persona_id and a["persona_id"] != persona_id:
                continue
            if metrica and not _asignacion_cuenta_metrica(a["delta"], metrica):
                continue
            eid = a["encuentro_id"]
            if eid not in eventos_map:
                eventos_map[eid] = {
                    "encuentro_id": eid,
                    "curso_nombre": a["curso_nombre"],
                    "plan_nombre": a["plan_nombre"],
                    "empresa_nombre": a["empresa_nombre"],
                    "fecha": a["fecha"],
                    "fecha_realizacion": a.get("fecha_realizacion"),
                    "capacitador": a["capacitador"],
                    "lugar": a["lugar"],
                    "link": a["link"],
                    "personas": [],
                }
            eventos_map[eid]["personas"].append(
                {
                    "persona_id": a["persona_id"],
                    "nombre": a["persona_nombre"],
                    "asistio": a["asistio"],
                    "nota": a["nota"],
                    "aprobo": a["aprobo"],
                }
            )
        return {
            "anio": anio,
            "nivel": "detalle",
            "mes": mes,
            "plan_id": plan_id,
            "persona_id": persona_id,
            "metrica": metrica,
            "eventos": list(eventos_map.values()),
        }

    if nivel == "personas":
        if not mes:
            raise ValueError("Seleccioná un mes para desglosar por persona")
        filas = []
        totales = _metricas_vacias()
        for pid in sorted(datos["nombres"].keys(), key=lambda x: datos["nombres"][x]):
            meses_data = datos["por_persona_mes"].get(pid, {})
            m = meses_data.get(mes, _metricas_vacias())
            if plan_id:
                # Recalcular solo asignaciones de ese plan
                m = _metricas_vacias()
                for a in datos["asignaciones"]:
                    if a["mes"] != mes or a["persona_id"] != pid:
                        continue
                    if a["plan_id"] != plan_id:
                        continue
                    _sumar_metricas(m, a["delta"])
                _finalizar_metricas(m)
            if metrica and (m.get(metrica, 0) or 0) == 0:
                continue
            if sum(m.get(k, 0) or 0 for k in METRICAS_RESUMEN[:4]) == 0 and m.get("pend_vencidos", 0) == 0:
                continue
            filas.append(_fila_metricas(pid, datos["nombres"][pid], m))
            _sumar_metricas(totales, m)
        _finalizar_metricas(totales)
        return {
            "anio": anio,
            "nivel": "personas",
            "mes": mes,
            "plan_id": plan_id,
            "metrica": metrica,
            "mes_nombre": MESES_NOMBRES[mes - 1] if 1 <= mes <= 12 else "",
            "plan_nombre": datos["plan_nombres"].get(plan_id or 0, ""),
            "filas": filas,
            "totales": totales,
        }

    if nivel == "planes":
        if not mes:
            raise ValueError("Seleccioná un mes para desglosar por plan")
        filas = []
        totales = _metricas_vacias()
        for plid in sorted(
            datos["plan_nombres"].keys(),
            key=lambda x: datos["plan_nombres"][x],
        ):
            meses_data = datos["por_plan_mes"].get(plid, {})
            m = meses_data.get(mes, _metricas_vacias())
            if metrica and m.get(metrica, 0) == 0:
                continue
            if sum(m.get(k, 0) or 0 for k in METRICAS_RESUMEN[:4]) == 0 and m.get("pend_vencidos", 0) == 0:
                continue
            filas.append(_fila_metricas(plid, datos["plan_nombres"][plid], m))
            _sumar_metricas(totales, m)
        _finalizar_metricas(totales)
        return {
            "anio": anio,
            "nivel": "planes",
            "mes": mes,
            "metrica": metrica,
            "mes_nombre": MESES_NOMBRES[mes - 1] if 1 <= mes <= 12 else "",
            "filas": filas,
            "totales": totales,
        }

    # nivel programas (default): filas = meses
    filas = []
    totales = _metricas_vacias()
    for i, nombre in enumerate(MESES_NOMBRES, start=1):
        m = datos["por_mes"][i]
        filas.append(_fila_metricas(i, nombre, m))
        _sumar_metricas(totales, m)
    _finalizar_metricas(totales)
    return {
        "anio": anio,
        "nivel": "programas",
        "filas": filas,
        "totales": totales,
    }


def matriz_tabla(
    empresa_id: int,
    *,
    anio: int | None = None,
    plan_ids: list[int] | None = None,
    tipos: list[str] | None = None,
    empresas: list[int] | None = None,
    persona_ids: list[int] | None = None,
    puesto_ids: list[int] | None = None,
    agrupar_por: str = "persona",
) -> dict:
    anio = anio or date.today().year
    plan_ids = plan_ids or []
    tipos = tipos or []
    persona_ids = persona_ids or []
    puesto_ids = puesto_ids or []
    empresas = empresas or []
    agrupar_por = (agrupar_por or "persona").lower()
    if agrupar_por not in ("persona", "puesto"):
        agrupar_por = "persona"

    datos = _colectar_datos_anuales(
        empresa_id,
        anio=anio,
        plan_ids=plan_ids,
        tipos=tipos,
        empresas=empresas,
        persona_ids=persona_ids,
        puesto_ids=puesto_ids,
    )
    por_persona_mes = datos["por_persona_mes"]
    por_puesto_mes = datos["por_puesto_mes"]
    nombres = datos["nombres"]
    puesto_nombres = datos["puesto_nombres"]

    filas = []
    if agrupar_por == "puesto":
        from gos.modulos.capacitacion.models import Puesto

        puestos_filtrados = Puesto.query.filter_by(empresa_id=empresa_id, activo=True)
        if puesto_ids:
            puestos_filtrados = puestos_filtrados.filter(Puesto.id.in_(puesto_ids))
        for puesto in puestos_filtrados.order_by(Puesto.nombre).all():
            puesto_nombres.setdefault(puesto.id, puesto.nombre)
        ids_ordenados = sorted(
            puesto_nombres.keys(),
            key=lambda x: (x == 0, puesto_nombres.get(x, "")),
        )
        for puid in ids_ordenados:
            meses_data = por_puesto_mes.get(puid, {m: _metricas_vacias() for m in range(1, 13)})
            anual = _metricas_vacias()
            meses_cortos = {}
            for mes in range(1, 13):
                m = meses_data.get(mes, _metricas_vacias())
                _sumar_metricas(anual, m)
                meses_cortos[str(mes)] = _a_metricas_cortas(m)
            _finalizar_metricas(anual)
            meses_cortos["anual"] = _a_metricas_cortas(anual)
            if sum(anual.get(k, 0) or 0 for k in ("programados", "pendientes", "cumplidos")) == 0:
                if puid not in por_puesto_mes and puesto_ids:
                    continue
            filas.append(
                {
                    "id": puid,
                    "nombre": puesto_nombres.get(puid, "Sin puesto"),
                    "meses": meses_cortos,
                }
            )
    else:
        personas_filtradas = _personas_filtradas(
            empresa_id, persona_ids=persona_ids, puesto_ids=puesto_ids
        )
        for persona in personas_filtradas:
            nombres.setdefault(persona.id, persona.nombre_completo)

        for pid in sorted(nombres.keys(), key=lambda x: nombres[x]):
            meses_data = por_persona_mes.get(pid, {m: _metricas_vacias() for m in range(1, 13)})
            anual = _metricas_vacias()
            meses_cortos = {}
            for mes in range(1, 13):
                m = meses_data.get(mes, _metricas_vacias())
                _sumar_metricas(anual, m)
                meses_cortos[str(mes)] = _a_metricas_cortas(m)
            _finalizar_metricas(anual)
            meses_cortos["anual"] = _a_metricas_cortas(anual)
            if sum(anual.get(k, 0) or 0 for k in ("programados", "pendientes", "cumplidos")) == 0:
                if pid not in por_persona_mes and (persona_ids or puesto_ids):
                    continue
            filas.append(
                {
                    "id": pid,
                    "nombre": nombres[pid],
                    "meses": meses_cortos,
                }
            )

    return {
        "anio": anio,
        "agrupar_por": agrupar_por,
        "meses": [{"num": i, "nombre": n} for i, n in enumerate(MESES_NOMBRES, start=1)],
        "filas": filas,
        "hoy": date.today().isoformat(),
    }


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
    agrupar_por: str = "persona",
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
            anio=anio,
            plan_ids=plan_ids,
            tipos=tipos,
            empresas=empresas,
            persona_ids=persona_ids,
            puesto_ids=puesto_ids,
            agrupar_por=agrupar_por,
        )

    return {"vista": vista, "filtros": filtros, "data": data}
