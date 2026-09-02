from gos.extensions import db
from gos.models import Perfil
from gos.services.modulo_service import MODULO_CODES, modulo_codes_activos


def listar_perfiles_empresa(empresa_id: int) -> list[Perfil]:
    return (
        Perfil.query.filter_by(empresa_id=empresa_id)
        .order_by(Perfil.nombre)
        .all()
    )


def _normalizar_modulos(modulos: list[str] | None) -> list[str]:
    if not modulos:
        return []
    permitidos = set(modulo_codes_activos())
    vistos: set[str] = set()
    resultado: list[str] = []
    for code in modulos:
        if code in MODULO_CODES and code in permitidos and code not in vistos:
            vistos.add(code)
            resultado.append(code)
    return resultado


def crear_perfil(
    *,
    empresa_id: int,
    nombre: str,
    modulos: list[str] | None,
) -> tuple[Perfil | None, str | None]:
    nombre = nombre.strip()
    if not nombre:
        return None, "El nombre del perfil es obligatorio."

    modulos_norm = _normalizar_modulos(modulos)
    if not modulos_norm:
        return None, "Seleccioná al menos un módulo."

    if Perfil.query.filter_by(empresa_id=empresa_id, nombre=nombre).first():
        return None, f"Ya existe un perfil llamado «{nombre}»."

    perfil = Perfil(empresa_id=empresa_id, nombre=nombre, modulos=modulos_norm)
    db.session.add(perfil)
    db.session.commit()
    return perfil, None


def actualizar_perfil(
    perfil: Perfil,
    *,
    nombre: str,
    modulos: list[str] | None,
) -> str | None:
    nombre = nombre.strip()
    if not nombre:
        return "El nombre del perfil es obligatorio."

    modulos_norm = _normalizar_modulos(modulos)
    if not modulos_norm:
        return "Seleccioná al menos un módulo."

    duplicado = (
        Perfil.query.filter(
            Perfil.empresa_id == perfil.empresa_id,
            Perfil.nombre == nombre,
            Perfil.id != perfil.id,
        ).first()
    )
    if duplicado:
        return f"Ya existe un perfil llamado «{nombre}»."

    perfil.nombre = nombre
    perfil.modulos = modulos_norm
    db.session.commit()
    return None


def eliminar_perfil(perfil: Perfil) -> str | None:
    if perfil.usuarios:
        cantidad = len(perfil.usuarios)
        return f"No se puede eliminar: {cantidad} usuario(s) tienen asignado este perfil."
    db.session.delete(perfil)
    db.session.commit()
    return None


# Perfiles base (placeholders de la UI). No había backup recuperable.
_PERFILES_BASE_FULL = (
    {
        "nombre": "Operaciones",
        "modulos": ["dashboard", "mantenimiento", "om", "recursos", "ralenti", "capacitacion"],
    },
    {
        "nombre": "Consultoría",
        "modulos": ["dashboard", "objetivos", "hwo", "vacaciones", "capacitacion"],
    },
    {
        "nombre": "Acceso completo",
        "modulos": list(MODULO_CODES),
    },
)

_PERFILES_BASE_OBJETIVOS = (
    {
        "nombre": "Operaciones",
        "modulos": ["dashboard", "mantenimiento", "om", "recursos", "ralenti"],
    },
    {
        "nombre": "Consultoría",
        "modulos": ["dashboard", "objetivos", "hwo", "vacaciones"],
    },
    {
        "nombre": "Acceso completo",
        "modulos": [
            "dashboard",
            "objetivos",
            "hwo",
            "vacaciones",
            "ralenti",
            "mantenimiento",
            "om",
            "recursos",
            "sgc",
        ],
    },
)

_PERFILES_BASE_CAP = (
    {
        "nombre": "Capacitación",
        "modulos": ["capacitacion"],
    },
    {
        "nombre": "Acceso completo",
        "modulos": ["capacitacion"],
    },
)


def _perfiles_base_para_modo() -> tuple[dict, ...]:
    try:
        from gos import env

        mode = env.app_mode()
    except Exception:
        return _PERFILES_BASE_FULL
    if mode == "capacitacion":
        return _PERFILES_BASE_CAP
    if mode == "objetivos":
        return _PERFILES_BASE_OBJETIVOS
    return _PERFILES_BASE_FULL


PERFILES_BASE = _PERFILES_BASE_FULL  # compat; restaurar usa _perfiles_base_para_modo


def upsert_perfiles_empresa(
    empresa_id: int,
    perfiles: list[dict],
) -> dict[str, int]:
    """Crea o actualiza perfiles por nombre. No borra perfiles ausentes en la lista."""
    creados = 0
    actualizados = 0
    for item in perfiles:
        nombre = (item.get("nombre") or "").strip()
        if not nombre:
            continue
        modulos_norm = _normalizar_modulos(item.get("modulos"))
        if not modulos_norm:
            continue
        existente = Perfil.query.filter_by(empresa_id=empresa_id, nombre=nombre).first()
        if existente:
            existente.modulos = modulos_norm
            actualizados += 1
        else:
            db.session.add(
                Perfil(empresa_id=empresa_id, nombre=nombre, modulos=modulos_norm)
            )
            creados += 1
    db.session.commit()
    return {"creados": creados, "actualizados": actualizados, "total": Perfil.query.filter_by(empresa_id=empresa_id).count()}


def restaurar_perfiles_base(empresa_id: int) -> dict[str, int]:
    return upsert_perfiles_empresa(empresa_id, list(_perfiles_base_para_modo()))


def exportar_perfiles_empresa(empresa_id: int) -> list[dict]:
    return [
        {"nombre": p.nombre, "modulos": list(p.modulos or [])}
        for p in listar_perfiles_empresa(empresa_id)
    ]
