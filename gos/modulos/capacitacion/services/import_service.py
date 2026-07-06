from __future__ import annotations

from io import BytesIO

import openpyxl

from gos.extensions import db
from gos.modulos.capacitacion.models import Curso, Participante, Puesto
from gos.modulos.capacitacion.services.taxonomia_service import (
    clasificacion_desde_legacy,
    tipo_capacitacion_legacy,
    validar_clasificacion,
)
from gos.modulos.capacitacion.services.catalogo_service import _parse_date, _parse_decimal, _parse_int
from gos.modulos.objetivos.models.catalogos import Sector


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
            "El Excel debe tener encabezados en la fila 1. Mínimo: nombre. "
            "Opcionales: apellido, dni, email, telefono, centro, sector_codigo, "
            "puesto_codigo, fecha_ingreso, observaciones. Obligatorio: nombre, legajo"
        )

    sectores = {s.codigo: s.id for s in Sector.query.filter_by(empresa_id=empresa_id, activo=True).all()}
    puestos = {p.codigo: p.id for p in Puesto.query.filter_by(empresa_id=empresa_id, activo=True).all()}
    legajos_existentes = {
        p.legajo for p in Participante.query.filter_by(empresa_id=empresa_id).all() if p.legajo
    }

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

        nombre = val("nombre")
        if not nombre:
            omitidos += 1
            continue

        legajo = val("legajo") or None
        if not legajo:
            errores.append(f"Fila {row_idx}: el legajo es obligatorio")
            continue
        sector_codigo = val("sector_codigo")
        puesto_codigo = val("puesto_codigo")
        sector_id = sectores.get(sector_codigo) if sector_codigo else None
        puesto_id = puestos.get(puesto_codigo) if puesto_codigo else None

        if sector_codigo and not sector_id:
            errores.append(f"Fila {row_idx}: sector «{sector_codigo}» no encontrado")
            continue
        if puesto_codigo and not puesto_id:
            errores.append(f"Fila {row_idx}: puesto «{puesto_codigo}» no encontrado")
            continue

        existente = None
        if legajo:
            existente = Participante.query.filter_by(empresa_id=empresa_id, legajo=legajo).first()

        try:
            fecha_ingreso = _parse_date(val("fecha_ingreso") or None)
        except ValueError:
            errores.append(f"Fila {row_idx}: fecha_ingreso inválida")
            continue

        data = {
            "nombre": nombre,
            "apellido": val("apellido") or None,
            "legajo": legajo,
            "dni": val("dni") or None,
            "email": val("email") or None,
            "telefono": val("telefono") or None,
            "centro": val("centro") or None,
            "observaciones": val("observaciones") or None,
            "sector_id": sector_id,
            "puesto_id": puesto_id,
            "fecha_ingreso": fecha_ingreso.isoformat() if fecha_ingreso else None,
        }

        if existente:
            from gos.modulos.capacitacion.services.catalogo_service import actualizar_participante

            try:
                actualizar_participante(empresa_id, existente.id, data)
            except ValueError as exc:
                errores.append(f"Fila {row_idx}: {exc}")
                continue
            actualizados += 1
        else:
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
