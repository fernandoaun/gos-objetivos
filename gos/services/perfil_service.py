from gos.extensions import db
from gos.models import Perfil
from gos.services.modulo_service import MODULO_CODES


def listar_perfiles_empresa(empresa_id: int) -> list[Perfil]:
    return (
        Perfil.query.filter_by(empresa_id=empresa_id)
        .order_by(Perfil.nombre)
        .all()
    )


def _normalizar_modulos(modulos: list[str] | None) -> list[str]:
    if not modulos:
        return []
    vistos: set[str] = set()
    resultado: list[str] = []
    for code in modulos:
        if code in MODULO_CODES and code not in vistos:
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
