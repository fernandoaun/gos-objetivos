from __future__ import annotations

from gos.extensions import db
from gos.modulos.capacitacion.models import Participante
from gos.modulos.capacitacion.services.catalogo_service import (
    crear_participante,
    centro_id_desde_texto,
    sector_id_desde_texto,
)

def sincronizar_legajos_vacaciones(empresa_id: int) -> dict:
    """
    Importa empleados desde el módulo Vacaciones (tabla vacaciones) que no existan
    en capacitación, emparejando por legajo. Sincroniza nombre, sector y fecha de ingreso.
    """
    try:
        from gos.modulos.vacaciones.database import get_session
        from gos.modulos.vacaciones.models import Vacacion
    except ImportError:
        raise ValueError("Módulo Vacaciones no disponible")

    creados = 0
    actualizados = 0
    omitidos = 0

    session = get_session()
    try:
        vac_rows = session.query(Vacacion).all()
        legajos_vistos: set[int] = set()
        for row in vac_rows:
            if row.legajo is None or row.legajo in legajos_vistos:
                continue
            legajos_vistos.add(row.legajo)
            legajo_str = str(row.legajo)
            nombre = (row.empleado or "").strip()
            if not nombre:
                omitidos += 1
                continue

            sector_id = sector_id_desde_texto(empresa_id, row.sector, crear_si_falta=False)
            fecha_ingreso = row.fecha_ingreso.isoformat() if row.fecha_ingreso else None
            centro_id = centro_id_desde_texto(empresa_id, row.centro)

            existente = Participante.query.filter_by(empresa_id=empresa_id, legajo=legajo_str).first()
            if existente:
                changed = False
                if not existente.activo:
                    existente.activo = True
                    changed = True
                if nombre and existente.nombre != nombre:
                    partes = nombre.split(None, 1)
                    existente.nombre = partes[0]
                    if len(partes) > 1:
                        existente.apellido = partes[1]
                    changed = True
                if sector_id and existente.sector_id != sector_id:
                    existente.sector_id = sector_id
                    changed = True
                if fecha_ingreso and (
                    not existente.fecha_ingreso
                    or existente.fecha_ingreso.isoformat() != fecha_ingreso
                ):
                    from datetime import date as date_cls

                    existente.fecha_ingreso = date_cls.fromisoformat(fecha_ingreso)
                    changed = True
                if centro_id and existente.centro_id != centro_id:
                    existente.centro_id = centro_id
                    changed = True
                if changed:
                    actualizados += 1
                else:
                    omitidos += 1
                continue

            partes = nombre.split(None, 1)
            payload = {
                "nombre": partes[0],
                "apellido": partes[1] if len(partes) > 1 else None,
                "legajo": legajo_str,
                "sector_id": sector_id,
                "centro_id": centro_id,
                "fecha_ingreso": fecha_ingreso,
            }
            try:
                crear_participante(empresa_id, payload)
                creados += 1
            except ValueError:
                omitidos += 1
    finally:
        session.close()

    db.session.commit()
    return {"creados": creados, "actualizados": actualizados, "omitidos": omitidos}
