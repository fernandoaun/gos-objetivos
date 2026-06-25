from __future__ import annotations

from io import BytesIO

import openpyxl

from gos.extensions import db
from gos.modulos.capacitacion.models import Curso, Participante, Puesto
from gos.modulos.capacitacion.models.catalogo import MODALIDADES, TIPOS_CAPACITACION
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
    required = {"nombre"}
    if not required.issubset(headers):
        raise ValueError(
            "El Excel debe tener encabezados en la fila 1. Mínimo: nombre. "
            "Opcionales: apellido, legajo, dni, email, telefono, sector_codigo, "
            "puesto_codigo, fecha_ingreso, observaciones"
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
            "observaciones": val("observaciones") or None,
            "sector_id": sector_id,
            "puesto_id": puesto_id,
            "fecha_ingreso": fecha_ingreso.isoformat() if fecha_ingreso else None,
        }

        if existente:
            from gos.modulos.capacitacion.services.catalogo_service import actualizar_participante

            actualizar_participante(empresa_id, existente.id, data)
            actualizados += 1
        else:
            if legajo and legajo in legajos_existentes:
                errores.append(f"Fila {row_idx}: legajo duplicado «{legajo}»")
                continue
            participante = Participante(
                empresa_id=empresa_id,
                nombre=nombre,
                apellido=data["apellido"],
                legajo=legajo,
                dni=data["dni"],
                email=data["email"],
                telefono=data["telefono"],
                observaciones=data["observaciones"],
                sector_id=sector_id,
                puesto_id=puesto_id,
                fecha_ingreso=fecha_ingreso,
            )
            db.session.add(participante)
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
            "Opcionales: descripcion, tipo_capacitacion, horas, modalidad, "
            "vigencia_meses, requiere_evaluacion, puntaje_minimo"
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
        if modalidad and modalidad not in MODALIDADES:
            errores.append(f"Fila {row_idx}: modalidad inválida")
            continue

        tipo = val("tipo_capacitacion").lower() or None
        if tipo and tipo not in TIPOS_CAPACITACION:
            errores.append(f"Fila {row_idx}: tipo_capacitacion inválido")
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
            curso.tipo_capacitacion = tipo
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
                    tipo_capacitacion=tipo,
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
