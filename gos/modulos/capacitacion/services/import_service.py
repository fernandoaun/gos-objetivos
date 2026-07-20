from __future__ import annotations

from io import BytesIO

import openpyxl

from gos.extensions import db
from gos.modulos.capacitacion.models import Centro, Curso, Participante
from gos.modulos.capacitacion.services.taxonomia_service import (
    clasificacion_desde_legacy,
    tipo_capacitacion_legacy,
    validar_clasificacion,
)
from gos.modulos.capacitacion.services.catalogo_service import (
    _parse_decimal,
    _parse_int,
    centro_id_desde_texto,
    puesto_id_desde_texto,
    sector_id_desde_texto,
)


def _cell_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _header_map(ws) -> dict[str, int]:
    headers = {}
    for col, cell in enumerate(ws[1], start=1):
        key = _cell_str(cell.value).lower().replace(" ", "_")
        if key:
            headers[key] = col
    return headers


def importar_participantes_excel(empresa_id: int, file_bytes: bytes) -> dict:
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb.active
    headers = _header_map(ws)
    required = {"nombre", "legajo"}
    if not required.issubset(headers):
        raise ValueError(
            "El Excel debe tener encabezados en la fila 1. Mínimo: nombre, legajo. "
            "Opcionales: apellido, email, centro, centro_codigo, sector, sector_codigo, "
            "puesto, puesto_codigo, observaciones. "
            "Si la persona ya existe (mismo legajo), solo se actualizan puesto, centro y sector."
        )

    legajos_existentes = {
        p.legajo for p in Participante.query.filter_by(empresa_id=empresa_id).all() if p.legajo
    }

    creados = actualizados = omitidos = 0
    errores: list[str] = []
    puestos_cambiaron = False

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(v is None or str(v).strip() == "" for v in row):
            continue

        def val(key: str):
            col = headers.get(key)
            if not col:
                return ""
            return _cell_str(row[col - 1])

        def val_any(*keys: str) -> str:
            for key in keys:
                value = val(key)
                if value:
                    return value
            return ""

        nombre = val("nombre")
        if not nombre:
            omitidos += 1
            continue

        legajo = val("legajo") or None
        if not legajo:
            errores.append(f"Fila {row_idx}: el legajo es obligatorio")
            continue

        sector_texto = val_any("sector_codigo", "sector")
        puesto_texto = val_any("puesto_codigo", "puesto")
        centro_codigo = val("centro_codigo")
        centro_texto = val_any("centro")

        sector_id = sector_id_desde_texto(empresa_id, sector_texto) if sector_texto else None
        puesto_id = (
            puesto_id_desde_texto(empresa_id, puesto_texto, sector_id=sector_id)
            if puesto_texto
            else None
        )
        centro_id = None
        if centro_codigo:
            centro = Centro.query.filter_by(
                empresa_id=empresa_id, codigo=centro_codigo, activo=True
            ).first()
            if not centro:
                errores.append(f"Fila {row_idx}: centro «{centro_codigo}» no encontrado")
                continue
            centro_id = centro.id
        elif centro_texto:
            centro_id = centro_id_desde_texto(empresa_id, centro_texto)

        existente = None
        if legajo:
            existente = Participante.query.filter_by(empresa_id=empresa_id, legajo=legajo).first()

        if existente:
            # Re-import: solo actualiza puesto / centro / sector (no pisa el resto).
            changed = False
            puesto_cambio = False
            if puesto_id is not None and existente.puesto_id != puesto_id:
                existente.puesto_id = puesto_id
                changed = True
                puesto_cambio = True
                puestos_cambiaron = True
            if centro_id is not None and existente.centro_id != centro_id:
                existente.centro_id = centro_id
                changed = True
            if sector_id is not None and existente.sector_id != sector_id:
                existente.sector_id = sector_id
                changed = True
            elif puesto_cambio and sector_id is None:
                # Si el Excel trae puesto pero no sector, alinear sector del puesto.
                from gos.modulos.capacitacion.models import Puesto

                puesto = Puesto.query.filter_by(id=puesto_id, empresa_id=empresa_id).first()
                if puesto and puesto.sector_id and existente.sector_id != puesto.sector_id:
                    existente.sector_id = puesto.sector_id
                    changed = True
            if changed:
                actualizados += 1
            else:
                omitidos += 1
            continue

        data = {
            "nombre": nombre,
            "apellido": val("apellido") or None,
            "legajo": legajo,
            "email": val("email") or None,
            "centro_id": centro_id,
            "observaciones": val("observaciones") or None,
            "sector_id": sector_id,
            "puesto_id": puesto_id,
        }

        if legajo and legajo in legajos_existentes:
            errores.append(f"Fila {row_idx}: legajo duplicado «{legajo}»")
            continue
        from gos.modulos.capacitacion.services.catalogo_service import crear_participante

        try:
            crear_participante(empresa_id, data)
        except ValueError as exc:
            errores.append(f"Fila {row_idx}: {exc}")
            continue
        if legajo:
            legajos_existentes.add(legajo)
        creados += 1

    db.session.commit()
    if puestos_cambiaron:
        from gos.modulos.capacitacion.services.acreditacion_service import refrescar_vigencias
        from gos.modulos.capacitacion.services.catalogo_service import desactivar_puestos_huerfanos

        desactivar_puestos_huerfanos(empresa_id, gracia_horas=None)
        refrescar_vigencias(empresa_id)
    return {"creados": creados, "actualizados": actualizados, "omitidos": omitidos, "errores": errores}


def importar_cursos_excel(empresa_id: int, file_bytes: bytes) -> dict:
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb.active
    headers = _header_map(ws)
    if "codigo" not in headers or "nombre" not in headers:
        raise ValueError(
            "El Excel debe tener encabezados: codigo, nombre. "
            "Opcionales: descripcion, categoria, tipo, origen, modalidad, horas, "
            "vigencia_meses, requiere_evaluacion, puntaje_minimo. "
            "Legado: tipo_capacitacion (se mapea a la cascada)"
        )

    creados = actualizados = omitidos = 0
    errores: list[str] = []

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(v is None or str(v).strip() == "" for v in row):
            continue

        def val(key: str):
            col = headers.get(key)
            if not col:
                return ""
            return _cell_str(row[col - 1])

        codigo = val("codigo")
        nombre = val("nombre")
        if not codigo or not nombre:
            omitidos += 1
            continue

        modalidad = val("modalidad").lower() or None
        categoria = val("categoria").lower() or None
        tipo = val("tipo").lower() or None
        origen = val("origen").lower() or None
        legacy_tipo = val("tipo_capacitacion").lower() or None

        if not categoria and legacy_tipo:
            categoria, tipo, origen = clasificacion_desde_legacy(empresa_id, legacy_tipo)

        try:
            categoria, tipo, origen, modalidad = validar_clasificacion(
                empresa_id, categoria, tipo, origen, modalidad
            )
        except ValueError as exc:
            errores.append(f"Fila {row_idx}: {exc}")
            continue

        try:
            horas = _parse_decimal(val("horas") or None)
            vigencia = _parse_int(val("vigencia_meses") or None)
            puntaje = _parse_decimal(val("puntaje_minimo") or None)
        except ValueError as exc:
            errores.append(f"Fila {row_idx}: {exc}")
            continue

        requiere_eval = val("requiere_evaluacion").lower() in ("1", "true", "si", "sí", "yes")

        curso = Curso.query.filter_by(empresa_id=empresa_id, codigo=codigo).first()
        if curso:
            curso.nombre = nombre
            curso.descripcion = val("descripcion") or None
            curso.categoria = categoria
            curso.tipo = tipo
            curso.origen = origen
            curso.tipo_capacitacion = tipo_capacitacion_legacy(categoria, tipo)
            curso.horas = horas
            curso.modalidad = modalidad
            curso.vigencia_meses = vigencia
            curso.requiere_evaluacion = requiere_eval
            curso.puntaje_minimo = puntaje
            curso.activo = True
            actualizados += 1
        else:
            db.session.add(
                Curso(
                    empresa_id=empresa_id,
                    codigo=codigo,
                    nombre=nombre,
                    descripcion=val("descripcion") or None,
                    categoria=categoria,
                    tipo=tipo,
                    origen=origen,
                    tipo_capacitacion=tipo_capacitacion_legacy(categoria, tipo),
                    horas=horas,
                    modalidad=modalidad,
                    vigencia_meses=vigencia,
                    requiere_evaluacion=requiere_eval,
                    puntaje_minimo=puntaje,
                )
            )
            creados += 1

    db.session.commit()
    return {"creados": creados, "actualizados": actualizados, "omitidos": omitidos, "errores": errores}
