"""Catálogo narrativo de módulos y submódulos para presentaciones GOS.

Estética y sentido alineados a las presentaciones de Abastecimiento / Mantenimiento:
portada oscura, statement de marca, flujo dato→decisión, KPIs y foco por área.
"""

from __future__ import annotations

from copy import deepcopy

# Colores de marca (presentaciones de referencia)
COLOR_GOLD = "FDBC0A"
COLOR_GREEN = "6DBB34"
COLOR_DARK = "262B31"
COLOR_DARK_ALT = "313640"
COLOR_GRAY = "D6D7D9"
COLOR_MUTED = "6B6E72"
COLOR_FOOTER = "C7C9CC"
COLOR_LIGHT = "F2F2F2"


def _mod(
    code: str,
    label: str,
    sistema: str,
    tagline: str,
    tagline_accent: str,
    pilares: list[str],
    callout: str,
    statement: str,
    statement_pilares: list[str],
    proceso: list[str],
    flujo: list[dict],
    overview_title: str,
    overview_highlight: str,
    overview_footer: str,
    submodulos: list[dict],
) -> dict:
    return {
        "code": code,
        "label": label,
        "sistema": sistema,
        "tagline": tagline,
        "tagline_accent": tagline_accent,
        "pilares": pilares,
        "callout": callout,
        "statement": statement,
        "statement_pilares": statement_pilares,
        "proceso": proceso,
        "flujo": flujo,
        "overview_title": overview_title,
        "overview_highlight": overview_highlight,
        "overview_footer": overview_footer,
        "submodulos": submodulos,
    }


CATALOG: dict[str, dict] = {
    "dashboard": _mod(
        code="dashboard",
        label="DashBoard",
        sistema="SISTEMA DE GESTIÓN INTEGRAL GOS",
        tagline="DashBoard",
        tagline_accent="que unifica la operación",
        pilares=["Visión · Alertas · Módulos · Decisión"],
        callout="Una sola vista para gobernar la plataforma",
        statement="Una operación eficiente se ve completa, no fragmentada.",
        statement_pilares=["Visibilidad · Prioridad · Acción · Mejora continua"],
        proceso=["VER", "PRIORIZAR", "ACTUAR", "MEDIR", "MEJORAR"],
        flujo=[
            {"title": "DATOS DE MÓDULOS", "subtitle": "fuentes operativas"},
            {"title": "GOS DASHBOARD", "subtitle": "visión unificada"},
            {"title": "ALERTAS Y KPIs", "subtitle": "señales tempranas"},
            {"title": "ACCIÓN", "subtitle": "decisiones oportunas"},
        ],
        overview_title="El Command Center concentra el estado de la plataforma",
        overview_highlight="estado de la plataforma",
        overview_footer="VISIÓN INTEGRAL",
        submodulos=[
            {
                "code": "command_center",
                "label": "Command Center",
                "eyebrow": "VISTA HOLOGRÁFICA",
                "title": "Un tablero para todos los módulos GOS",
                "highlight": "todos los módulos GOS",
                "bullets": [
                    "Consolida señales de Objetivos, Capacitación, Mantenimiento, Vacaciones, Ralentí, Análisis y O&M.",
                    "Prioriza alertas y desvíos para actuar antes de que impacten la operación.",
                    "Sirve como puerta de entrada ejecutiva a cada módulo de la plataforma.",
                ],
                "footer": "COMMAND CENTER",
            }
        ],
    ),
    "objetivos": _mod(
        code="objetivos",
        label="Objetivos",
        sistema="SISTEMA DE PLANEAMIENTO ESTRATÉGICO",
        tagline="Objetivos",
        tagline_accent="que alinean la operación",
        pilares=["FODA · Estrategia · Metas · KPI"],
        callout="Resultados, seguimiento y mejora continua",
        statement="Una estrategia clara convierte el diagnóstico en acción medible.",
        statement_pilares=["Diagnóstico · Objetivos · Indicadores · Seguimiento"],
        proceso=["DIAGNOSTICAR", "DEFINIR", "MEDIR", "SEGUIR", "AJUSTAR"],
        flujo=[
            {"title": "FODA / DAFO", "subtitle": "diagnóstico"},
            {"title": "OBJETIVOS", "subtitle": "dirección estratégica"},
            {"title": "KPI Y METAS", "subtitle": "medición"},
            {"title": "ACCIÓN", "subtitle": "planes y reportes"},
        ],
        overview_title="Objetivos integra diagnóstico, meta e indicador",
        overview_highlight="diagnóstico, meta e indicador",
        overview_footer="PLANEAMIENTO",
        submodulos=[
            {
                "code": "dashboard",
                "label": "Dashboard",
                "eyebrow": "TABLERO ESTRATÉGICO",
                "title": "El tablero resume avance y desvíos",
                "highlight": "avance y desvíos",
                "bullets": [
                    "Muestra el estado de objetivos, metas y KPI en una sola lectura.",
                    "Facilita el seguimiento ejecutivo sin perder el detalle operativo.",
                    "Conecta la estrategia con lo que ocurre mes a mes.",
                ],
                "footer": "DASHBOARD",
            },
            {
                "code": "foda",
                "label": "FODA",
                "eyebrow": "DIAGNÓSTICO",
                "title": "El FODA ordena fortalezas, riesgos y oportunidades",
                "highlight": "fortalezas, riesgos y oportunidades",
                "bullets": [
                    "Estructura el análisis interno y externo en una matriz accionable.",
                    "Sirve de base para priorizar objetivos estratégicos.",
                    "Permite exportar y comunicar el diagnóstico con claridad.",
                ],
                "footer": "FODA / DAFO",
            },
            {
                "code": "estrategicos",
                "label": "Objetivos Estratégicos",
                "eyebrow": "DIRECCIÓN",
                "title": "Los objetivos traducen la estrategia en compromisos",
                "highlight": "compromisos",
                "bullets": [
                    "Definen qué se busca lograr y con qué horizonte.",
                    "Vinculan el diagnóstico FODA con metas e indicadores.",
                    "Dan trazabilidad a la gestión del planeamiento.",
                ],
                "footer": "OBJETIVOS",
            },
            {
                "code": "kpi",
                "label": "KPI",
                "eyebrow": "MEDICIÓN",
                "title": "Los KPI convierten el avance en evidencia",
                "highlight": "evidencia",
                "bullets": [
                    "Registran series, metas y tipos de medición por indicador.",
                    "Permiten comparar desempeño real vs esperado.",
                    "Sostienen reportes y decisiones de mejora.",
                ],
                "footer": "KPI",
            },
            {
                "code": "reportes",
                "label": "Reportes",
                "eyebrow": "COMUNICACIÓN",
                "title": "Los reportes cierran el ciclo de seguimiento",
                "highlight": "ciclo de seguimiento",
                "bullets": [
                    "Resumen el estado del planeamiento para auditoría y dirección.",
                    "Facilitan la lectura de avances, brechas y prioridades.",
                    "Conectan indicadores con la narrativa de gestión.",
                ],
                "footer": "REPORTES",
            },
            {
                "code": "configuracion",
                "label": "Configuración",
                "eyebrow": "GOBIERNO",
                "title": "La configuración sostiene reglas y catálogos",
                "highlight": "reglas y catálogos",
                "bullets": [
                    "Define parámetros de planeamiento por empresa.",
                    "Asegura consistencia en catálogos y mediciones.",
                    "Reduce fricción al cargar y seguir indicadores.",
                ],
                "footer": "CONFIGURACIÓN",
            },
        ],
    ),
    "capacitacion": _mod(
        code="capacitacion",
        label="Capacitación",
        sistema="SISTEMA DE GESTIÓN DE CAPACITACIÓN",
        tagline="Capacitación",
        tagline_accent="que habilita al personal",
        pilares=["Planes de carrera · Matriz · Evidencias · Cumplimiento"],
        callout="Competencias, trazabilidad y mejora continua",
        statement="Una operación segura comienza con personas formadas y vigentes.",
        statement_pilares=["Requisitos · Planes de carrera · Evidencia · Alertas"],
        proceso=["PLANIFICAR", "DICTAR", "REGISTRAR", "ACREDITAR", "ALERTAR", "MEJORAR"],
        flujo=[
            {"title": "REQUISITOS", "subtitle": "por puesto / norma"},
            {"title": "PLANES DE CARRERA", "subtitle": "planes y encuentros"},
            {"title": "MATRIZ", "subtitle": "cumplimiento"},
            {"title": "ACCIÓN", "subtitle": "alertas y reportes ISO"},
        ],
        overview_title="Capacitación integra requisito, evidencia y vigencia",
        overview_highlight="requisito, evidencia y vigencia",
        overview_footer="FORMACIÓN",
        submodulos=[
            {
                "code": "dashboard",
                "label": "Dashboard",
                "eyebrow": "PANEL",
                "title": "El panel muestra cumplimiento y vencimientos",
                "highlight": "cumplimiento y vencimientos",
                "bullets": [
                    "Resume cobertura de formación y focos de riesgo.",
                    "Prioriza alertas de vigencia y brechas por curso o tipo.",
                    "Sirve de brújula diaria para RR.HH. y operación.",
                ],
                "footer": "DASHBOARD",
            },
            {
                "code": "matriz",
                "label": "Matriz analítica",
                "eyebrow": "ANALÍTICA",
                "title": "La matriz cruza personas, puestos y requisitos",
                "highlight": "personas, puestos y requisitos",
                "bullets": [
                    "Visualiza quién cumple, quién vence y quién falta formar.",
                    "Filtra por sector, curso y estado para decidir prioridades.",
                    "Soporta auditoría con evidencia trazable.",
                ],
                "footer": "MATRIZ",
            },
            {
                "code": "cronograma",
                "label": "Cronograma",
                "eyebrow": "PLANIFICACIÓN",
                "title": "El cronograma ordena la demanda de formación",
                "highlight": "demanda de formación",
                "bullets": [
                    "Programa encuentros y cobertura por puesto.",
                    "Anticipa carga de instructores y disponibilidad.",
                    "Cierra el circuito entre requisito y ejecución.",
                ],
                "footer": "CRONOGRAMA",
            },
            {
                "code": "programas",
                "label": "Planes de carrera",
                "eyebrow": "EJECUCIÓN",
                "title": "Los planes de carrera agrupan planes, cursos y puestos",
                "highlight": "planes, cursos y puestos",
                "bullets": [
                    "Definen qué se dicta, a quién y con qué vigencia.",
                    "Registran inscripciones y encuentros.",
                    "Conectan el plan anual con la operación diaria.",
                ],
                "footer": "PLANES DE CARRERA",
            },
            {
                "code": "personas",
                "label": "Personas",
                "eyebrow": "PARTICIPANTES",
                "title": "El legajo de formación sigue a cada persona",
                "highlight": "cada persona",
                "bullets": [
                    "Centraliza historial, acreditaciones y certificados.",
                    "Sincroniza con vacaciones / legajos cuando corresponde.",
                    "Facilita la lectura individual para jefatura y auditoría.",
                ],
                "footer": "PERSONAS",
            },
            {
                "code": "catalogos",
                "label": "Cursos y catálogos",
                "eyebrow": "CATÁLOGO",
                "title": "El catálogo estandariza cursos y taxonomías",
                "highlight": "cursos y taxonomías",
                "bullets": [
                    "Ordena tipos de certificación, cursos e instructores.",
                    "Evita duplicados y mejora la calidad del dato.",
                    "Es la base para requisitos y reportes ISO.",
                ],
                "footer": "CATÁLOGOS",
            },
            {
                "code": "reportes",
                "label": "Reportes ISO",
                "eyebrow": "AUDITORÍA",
                "title": "Los reportes ISO documentan el sistema de formación",
                "highlight": "sistema de formación",
                "bullets": [
                    "Exponen cumplimiento y evidencias para auditoría.",
                    "Resumen el estado general del plan de carrera.",
                    "Cierran el ciclo de mejora con datos exportables.",
                ],
                "footer": "REPORTES ISO",
            },
            {
                "code": "alertas",
                "label": "Alertas",
                "eyebrow": "ANTICIPACIÓN",
                "title": "Las alertas anticipan vencimientos y brechas",
                "highlight": "vencimientos y brechas",
                "bullets": [
                    "Avisan certificaciones por vencer o faltantes.",
                    "Permiten notificar a responsables a tiempo.",
                    "Reducen riesgo operativo y de no conformidad.",
                ],
                "footer": "ALERTAS",
            },
            {
                "code": "configuracion",
                "label": "Configuración",
                "eyebrow": "PARÁMETROS",
                "title": "La configuración define vigencias y reglas",
                "highlight": "vigencias y reglas",
                "bullets": [
                    "Ajusta períodos, umbrales y parámetros del módulo.",
                    "Mantiene coherencia entre requisitos y alertas.",
                    "Sostiene la operación sin depender de ajustes manuales.",
                ],
                "footer": "CONFIGURACIÓN",
            },
        ],
    ),
    "hwo": _mod(
        code="hwo",
        label="Análisis",
        sistema="SISTEMA DE ANÁLISIS OPERATIVO",
        tagline="Análisis",
        tagline_accent="que explica la operación",
        pilares=["Equipos · Incidencias · Tendencias · Decisión"],
        callout="Datos, patrones y mejora continua",
        statement="Una decisión oportuna nace de un análisis confiable.",
        statement_pilares=["Datos · Lectura · Tendencia · Acción"],
        proceso=["CARGAR", "ANALIZAR", "COMPARAR", "DECIDIR", "MEJORAR"],
        flujo=[
            {"title": "DATASETS", "subtitle": "fuentes HWO"},
            {"title": "GOS ANÁLISIS", "subtitle": "tablero operativo"},
            {"title": "TENDENCIAS", "subtitle": "patrones"},
            {"title": "ACCIÓN", "subtitle": "prioridad operativa"},
        ],
        overview_title="Análisis transforma registros en prioridades",
        overview_highlight="prioridades",
        overview_footer="ANÁLISIS",
        submodulos=[
            {
                "code": "dashboard",
                "label": "Dashboard",
                "eyebrow": "TABLERO",
                "title": "El dashboard muestra equipos e incidencias",
                "highlight": "equipos e incidencias",
                "bullets": [
                    "Consolida datasets operativos para lectura rápida.",
                    "Facilita comparar modalidades y detectar focos.",
                    "Apoya la conversación entre operación y dirección.",
                ],
                "footer": "DASHBOARD",
            }
        ],
    ),
    "vacaciones": _mod(
        code="vacaciones",
        label="Vacaciones",
        sistema="SISTEMA DE GESTIÓN DE VACACIONES Y HORAS",
        tagline="Vacaciones",
        tagline_accent="que ordenan la gente",
        pilares=["Adeudados · Horas · Importación · Trazabilidad"],
        callout="Saldo, cobertura y mejora continua",
        statement="Una operación estable planifica el descanso y controla las horas.",
        statement_pilares=["Saldo · Cobertura · Registro · Control"],
        proceso=["IMPORTAR", "CONTROLAR", "PLANIFICAR", "CUBRIR", "MEJORAR"],
        flujo=[
            {"title": "EXCEL / LEGAJOS", "subtitle": "carga inicial"},
            {"title": "SALDOS", "subtitle": "días adeudados"},
            {"title": "TOT HS", "subtitle": "horas trabajadas"},
            {"title": "ACCIÓN", "subtitle": "cobertura operativa"},
        ],
        overview_title="Vacaciones integra saldo, horas y cobertura",
        overview_highlight="saldo, horas y cobertura",
        overview_footer="PERSONAS",
        submodulos=[
            {
                "code": "adeudadas",
                "label": "Vacaciones adeudadas",
                "eyebrow": "SALDOS",
                "title": "El saldo adeudado hace visible la deuda de descanso",
                "highlight": "deuda de descanso",
                "bullets": [
                    "Muestra días pendientes por empleado.",
                    "Ayuda a planificar liberaciones sin romper cobertura.",
                    "Reduce reclamos por falta de trazabilidad.",
                ],
                "footer": "ADEUDADAS",
            },
            {
                "code": "tot_hs",
                "label": "Tot Hs.",
                "eyebrow": "HORAS",
                "title": "Tot Hs. complementa el control de carga laboral",
                "highlight": "carga laboral",
                "bullets": [
                    "Registra totales de horas para seguimiento gerencial.",
                    "Complementa la lectura de vacaciones con esfuerzo real.",
                    "Soporta conversaciones de planificación de personal.",
                ],
                "footer": "TOT HS",
            },
            {
                "code": "importar",
                "label": "Importar datos",
                "eyebrow": "CARGA",
                "title": "La importación acelera la actualización del padrón",
                "highlight": "actualización del padrón",
                "bullets": [
                    "Ingresa planillas Excel sin carga manual masiva.",
                    "Preserva trazabilidad del origen del dato.",
                    "Mantiene el módulo alineado con RR.HH.",
                ],
                "footer": "IMPORTAR",
            },
        ],
    ),
    "ralenti": _mod(
        code="ralenti",
        label="Ralentí",
        sistema="SISTEMA DE GESTIÓN DE RALENTÍ",
        tagline="Ralentí",
        tagline_accent="que cuida el consumo",
        pilares=["Horas · Consumo · Unidades · Compliance"],
        callout="Eficiencia, control y mejora continua",
        statement="Una flota eficiente reduce ralentí innecesario y costo oculto.",
        statement_pilares=["Medición · Cumplimiento · Unidad · Acción"],
        proceso=["CARGAR", "MEDIR", "COMPARAR", "ALERTAR", "MEJORAR"],
        flujo=[
            {"title": "ARCHIVOS", "subtitle": "telemetría / reportes"},
            {"title": "EVENTOS", "subtitle": "horas de ralentí"},
            {"title": "COMPLIANCE", "subtitle": "por unidad"},
            {"title": "ACCIÓN", "subtitle": "bajar consumo"},
        ],
        overview_title="Ralentí convierte horas paradas en señal de gestión",
        overview_highlight="señal de gestión",
        overview_footer="EFICIENCIA",
        submodulos=[
            {
                "code": "dashboard",
                "label": "Dashboard",
                "eyebrow": "CONSUMO",
                "title": "El tablero prioriza unidades con mayor ralentí",
                "highlight": "mayor ralentí",
                "bullets": [
                    "Muestra horas, consumo y cumplimiento por unidad.",
                    "Facilita detectar desvíos y conversar con operación.",
                    "Apoya metas de eficiencia energética de flota.",
                ],
                "footer": "DASHBOARD",
            }
        ],
    ),
    "mantenimiento": _mod(
        code="mantenimiento",
        label="Mantenimiento",
        sistema="SISTEMA DE GESTIÓN DE MANTENIMIENTO",
        tagline="Mantenimiento",
        tagline_accent="que sostiene la operación",
        pilares=["Correctivo · Preventivo · Flota · Talleres · Seguridad"],
        callout="Disponibilidad, cumplimiento y mejora continua",
        statement="Un mantenimiento preventivo sostiene una operación confiable.",
        statement_pilares=["Prevención · Disponibilidad · Seguridad · Mejora continua"],
        proceso=["PLANIFICAR", "EJECUTAR", "CONTROLAR", "REGISTRAR", "ANALIZAR", "MEJORAR"],
        flujo=[
            {"title": "BASE HISTÓRICA", "subtitle": "órdenes y tareas"},
            {"title": "GOS OBJETIVOS", "subtitle": "trazabilidad operativa"},
            {"title": "PLAN + VTV", "subtitle": "control preventivo y legal"},
            {"title": "ACCIÓN", "subtitle": "disponibilidad de flota"},
        ],
        overview_title="Mantenimiento integra disponibilidad, prevención y control",
        overview_highlight="disponibilidad, prevención y control",
        overview_footer="VISIÓN INTEGRAL",
        submodulos=[
            {
                "code": "plan",
                "label": "Plan preventivo",
                "eyebrow": "PREVENCIÓN",
                "title": "El plan preventivo anticipa fallas de flota",
                "highlight": "fallas de flota",
                "bullets": [
                    "Programa intervenciones antes del correctivo urgente.",
                    "Eleva disponibilidad y reduce tiempos fuera de servicio.",
                    "Conecta el tablero mensual con el cumplimiento del plan.",
                ],
                "footer": "PLAN PREVENTIVO",
            },
            {
                "code": "vtv",
                "label": "VTV",
                "eyebrow": "CUMPLIMIENTO LEGAL",
                "title": "VTV asegura habilitación legal de la flota",
                "highlight": "habilitación legal",
                "bullets": [
                    "Controla vencimientos y renovaciones por unidad.",
                    "Anticipa alertas para no operar fuera de norma.",
                    "Integra el control legal al circuito de mantenimiento.",
                ],
                "footer": "VTV",
            },
            {
                "code": "reporte_mensual",
                "label": "Reporte mensual",
                "eyebrow": "TABLERO",
                "title": "El reporte mensual resume carga y desempeño",
                "highlight": "carga y desempeño",
                "bullets": [
                    "Agrupa tareas, horas y categorías del período.",
                    "Sirve para revisar resultados con operación y dirección.",
                    "Alimenta la mejora continua del sector.",
                ],
                "footer": "REPORTE MENSUAL",
            },
            {
                "code": "importar",
                "label": "Importar",
                "eyebrow": "DATOS",
                "title": "La importación mantiene viva la base histórica",
                "highlight": "base histórica",
                "bullets": [
                    "Actualiza órdenes y tareas desde planillas operativas.",
                    "Preserva trazabilidad del período cargado.",
                    "Evita pérdida de continuidad en el análisis.",
                ],
                "footer": "IMPORTAR",
            },
        ],
    ),
    "om": _mod(
        code="om",
        label="O&M",
        sistema="SISTEMA DE APERTURA DE MÓDULOS O&M",
        tagline="O&M",
        tagline_accent="que abre la operación",
        pilares=["Personal · Unidades · Herramientas · Insumos"],
        callout="Dotación, recursos y mejora continua",
        statement="Una apertura ordenada evita improvisar en el frente.",
        statement_pilares=["Personal · Equipos · Materiales · Control"],
        proceso=["DEFINIR", "ASIGNAR", "CONTROLAR", "AUDITAR", "MEJORAR"],
        flujo=[
            {"title": "MÓDULO", "subtitle": "apertura O&M"},
            {"title": "RECURSOS", "subtitle": "personas y unidades"},
            {"title": "INSUMOS", "subtitle": "herramientas y materiales"},
            {"title": "ACCIÓN", "subtitle": "operar con control"},
        ],
        overview_title="O&M integra personal, flota e insumos del módulo",
        overview_highlight="personal, flota e insumos",
        overview_footer="APERTURA",
        submodulos=[
            {
                "code": "apertura",
                "label": "Apertura de módulos",
                "eyebrow": "DOTACIÓN",
                "title": "La apertura define qué se necesita para operar",
                "highlight": "para operar",
                "bullets": [
                    "Lista personal, unidades, herramientas e insumos por módulo.",
                    "Da trazabilidad a cambios y auditorías.",
                    "Reduce omisiones al movilizar un frente o base.",
                ],
                "footer": "APERTURA",
            }
        ],
    ),
}


def get_module(code: str) -> dict | None:
    mod = CATALOG.get(code)
    return deepcopy(mod) if mod else None


def list_modules_for_user(allowed_codes: set[str] | None) -> list[dict]:
    items = []
    for code, mod in CATALOG.items():
        if allowed_codes is not None and code not in allowed_codes:
            continue
        items.append(
            {
                "code": mod["code"],
                "label": mod["label"],
                "sistema": mod["sistema"],
                "description": f"{mod['tagline']} {mod['tagline_accent']}",
                "submodulos": [
                    {"code": s["code"], "label": s["label"]} for s in mod["submodulos"]
                ],
            }
        )
    return items


def resolve_submodulos(module_code: str, selected: list[str] | None) -> list[dict]:
    mod = get_module(module_code)
    if not mod:
        raise ValueError(f"Módulo desconocido: {module_code}")
    if not selected:
        return mod["submodulos"]
    wanted = set(selected)
    found = [s for s in mod["submodulos"] if s["code"] in wanted]
    if not found:
        raise ValueError("Ningún submódulo válido seleccionado.")
    return found
