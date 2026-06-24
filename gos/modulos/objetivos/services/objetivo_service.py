from datetime import date

from sqlalchemy import func

from gos.extensions import db
from gos.modulos.objetivos.models.objetivo import OBJETIVO_ESTADOS, Objetivo

PLANTILLA_2026 = [
    {
        "nombre": "Expansión y optimización tecnológica de las plantas de tratamiento de fluidos / Flowback",
        "descripcion": (
            "Incrementar la capacidad operativa de las plantas de tratamiento de fluidos para agua "
            "de flowback y disposición en sumideros, incorporando mejoras tecnológicas que permitan "
            "optimizar los procesos, mejorar la eficiencia en el uso de químicos y habilitar la "
            "reutilización del agua."
        ),
        "responsable_texto": "Gerencia de PCL",
    },
    {
        "nombre": "Migración tecnológica de la flota de equipos Hot Water hacia sistemas eléctricos",
        "descripcion": (
            "Incorporar tecnología eléctrica en los equipos Hot Water mediante nuevas unidades y "
            "conversión de equipos existentes, con el fin de mejorar la eficiencia energética y "
            "reducir el consumo de combustibles fósiles."
        ),
        "responsable_texto": "Gerencias: General - mantenimiento - PCL",
    },
    {
        "nombre": "Consolidación de la línea de servicios de Operación y Mantenimiento (O&M)",
        "descripcion": (
            "Consolidar la línea de O&M como unidad de negocio estratégica para GOS, ampliando "
            "contratos, desarrollando capacidades operativas específicas y estructurando equipos "
            "dedicados dentro del sector energético."
        ),
        "responsable_texto": "Gerencia General / Operaciones",
    },
    {
        "nombre": "Fortalecimiento de la estructura organizacional y desarrollo técnico",
        "descripcion": (
            "Acompañar el crecimiento fortaleciendo la estructura organizacional de GOS, "
            "incorporando áreas de soporte técnico como ingeniería y desarrollo, profesionalizando "
            "procesos internos y promoviendo la capacitación y certificación del personal."
        ),
        "responsable_texto": "Gerencia General / Operaciones",
    },
    {
        "nombre": "Desarrollo de nuevas líneas de servicios",
        "descripcion": (
            "Ampliar el portafolio de servicios de GOS implementando nuevas líneas de negocio "
            "orientadas a la industria energética, incluyendo bombeo de alta presión y "
            "mantenimiento de caminos en áreas operativas."
        ),
        "responsable_texto": "Gerencia General / Operaciones",
    },
    {
        "nombre": "Consolidación y expansión de la plataforma digital GOS Connect para la gestión integral de operaciones",
        "descripcion": (
            "Consolidar y expandir la plataforma digital GOS Connect como sistema integrado de "
            "gestión, centralizando la planificación operativa, el monitoreo, la transmisión de "
            "datos y el acceso en tiempo real para uso interno y de clientes."
        ),
        "responsable_texto": "Gerencia General / Operaciones",
    },
    {
        "nombre": "Sostenimiento de la rentabilidad y generación de valor económico",
        "descripcion": (
            "Asegurar la sostenibilidad económica mediante la gestión eficiente de recursos, "
            "control de costos y desarrollo de servicios rentables que generen valor para la "
            "empresa y sus accionistas."
        ),
        "responsable_texto": "Gerencias: General-PCL-Abastecimiento",
    },
    {
        "nombre": "Consolidar la cultura de seguridad, salud, medio ambiente y sustentabilidad",
        "descripcion": (
            "Fortalecer la gestión de Seguridad, Salud, Medio Ambiente y Sustentabilidad mediante "
            "la prevención de incidentes, mejora de condiciones de trabajo, reducción del impacto "
            "ambiental y optimización del uso de energía."
        ),
        "responsable_texto": "Gerencia General / Operaciones",
    },
    {
        "nombre": "Implementación del programa institucional de Diversidad, Equidad e Inclusión (DEI)",
        "descripcion": (
            "Implementar un programa de DEI que promueva un entorno laboral respetuoso, fomente "
            "oportunidades equitativas y establezca políticas organizacionales orientadas al "
            "desarrollo humano."
        ),
        "responsable_texto": "Gerencia General / Operaciones",
    },
    {
        "nombre": "Certificación del Sistema de Gestión Integrado (Tri-Norma)",
        "descripcion": (
            "Obtener la certificación del Sistema de Gestión Integrado bajo normas internacionales "
            "(ISO 9001, ISO 14001, ISO 45001), fortaleciendo procesos internos y una cultura de "
            "mejora continua."
        ),
        "responsable_texto": "Gerencia General / Operaciones",
    },
]

FECHA_INICIO_2026 = date(2025, 12, 21)
FECHA_FIN_2026 = date(2026, 12, 20)


def listar_objetivos(empresa_id: int) -> list[Objetivo]:
    return (
        Objetivo.query.filter_by(empresa_id=empresa_id, activo=True)
        .order_by(Objetivo.orden, Objetivo.id)
        .all()
    )


def obtener_objetivo(empresa_id: int, objetivo_id: int) -> Objetivo | None:
    return Objetivo.query.filter_by(id=objetivo_id, empresa_id=empresa_id, activo=True).first()


def _siguiente_codigo(empresa_id: int) -> str:
    count = Objetivo.query.filter_by(empresa_id=empresa_id, activo=True).count()
    return f"OE-{count + 1:02d}"


def _validar_campos(
    nombre: str,
    descripcion: str,
    estado: str | None = None,
) -> tuple[str, str, str]:
    nom = nombre.strip()
    desc = descripcion.strip()
    if len(nom) < 3:
        raise ValueError("El objetivo debe tener al menos 3 caracteres.")
    if len(desc) < 10:
        raise ValueError("La descripción debe tener al menos 10 caracteres.")
    est = (estado or "activo").strip()
    if est not in OBJETIVO_ESTADOS:
        raise ValueError("Estado inválido.")
    return nom, desc, est


def crear_objetivo(
    empresa_id: int,
    nombre: str,
    descripcion: str,
    responsable_texto: str | None = None,
    responsable_id: int | None = None,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
    estado: str = "activo",
) -> Objetivo:
    nom, desc, est = _validar_campos(nombre, descripcion, estado)
    max_orden = (
        db.session.query(func.max(Objetivo.orden))
        .filter_by(empresa_id=empresa_id, activo=True)
        .scalar()
        or 0
    )
    obj = Objetivo(
        empresa_id=empresa_id,
        codigo=_siguiente_codigo(empresa_id),
        nombre=nom,
        descripcion=desc,
        responsable_texto=(responsable_texto or "").strip() or None,
        responsable_id=responsable_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado=est,
        orden=max_orden + 1,
        origen="manual",
        activo=True,
    )
    db.session.add(obj)
    db.session.commit()
    return obj


def actualizar_objetivo(
    empresa_id: int,
    objetivo_id: int,
    nombre: str,
    descripcion: str,
    responsable_texto: str | None = None,
    responsable_id: int | None = None,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
    estado: str | None = None,
    clear_responsable: bool = False,
) -> Objetivo:
    obj = obtener_objetivo(empresa_id, objetivo_id)
    if not obj:
        raise ValueError("Objetivo no encontrado.")
    nom, desc, est = _validar_campos(nombre, descripcion, estado or obj.estado)
    obj.nombre = nom
    obj.descripcion = desc
    obj.responsable_texto = (responsable_texto or "").strip() or None
    obj.fecha_inicio = fecha_inicio
    obj.fecha_fin = fecha_fin
    obj.estado = est
    if clear_responsable:
        obj.responsable_id = None
    elif responsable_id:
        obj.responsable_id = responsable_id
    db.session.commit()
    return obj


def eliminar_objetivo(empresa_id: int, objetivo_id: int) -> None:
    obj = obtener_objetivo(empresa_id, objetivo_id)
    if not obj:
        raise ValueError("Objetivo no encontrado.")
    obj.activo = False
    db.session.commit()


def cargar_plantilla_2026(empresa_id: int) -> int:
    if Objetivo.query.filter_by(empresa_id=empresa_id, activo=True).count() > 0:
        raise ValueError("Ya hay objetivos cargados. Agregá nuevos manualmente o eliminá los existentes.")
    creados = 0
    for i, data in enumerate(PLANTILLA_2026, start=1):
        db.session.add(
            Objetivo(
                empresa_id=empresa_id,
                codigo=f"OE-{i:02d}",
                nombre=data["nombre"],
                descripcion=data["descripcion"],
                responsable_texto=data["responsable_texto"],
                fecha_inicio=FECHA_INICIO_2026,
                fecha_fin=FECHA_FIN_2026,
                estado="activo",
                orden=i,
                origen="plantilla",
                activo=True,
            )
        )
        creados += 1
    db.session.commit()
    return creados
