"""Exportación PDF de reportes de capacitación."""
from __future__ import annotations

import io
import xml.sax.saxutils as saxutils
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from gos.modulos.capacitacion.services.analitico_service import analitico_participante
from gos.modulos.capacitacion.services.reporte_service import NORMAS_ISO, reporte_iso, resumen_general_auditoria

_ESTADO_LABELS = {
    "cumplido": "Cumplido",
    "pendiente": "Pendiente",
    "vencido": "Vencido",
    "proximo_vencer": "Próximo a vencer",
}


def _base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CapTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=6))
    styles.add(ParagraphStyle(name="CapSub", parent=styles["Normal"], fontSize=9, textColor=colors.grey))
    styles.add(ParagraphStyle(name="CapH3", parent=styles["Heading3"], fontSize=11, spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="CapCell", parent=styles["Normal"], fontSize=8, leading=10))
    return styles


def generar_pdf_participante(empresa_nombre: str, participante_id: int, empresa_id: int) -> bytes:
    data = analitico_participante(participante_id, empresa_id=empresa_id)
    p = data["participante"]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = _base_styles()
    story = [
        Paragraph("Reporte individual de capacitación", styles["CapTitle"]),
        Paragraph(
            f"{saxutils.escape(empresa_nombre)} · {saxutils.escape(p['nombre'])} · "
            f"Legajo {saxutils.escape(p.get('legajo') or '—')} · {datetime.now().strftime('%d/%m/%Y')}",
            styles["CapSub"],
        ),
        Spacer(1, 10),
        Paragraph(
            f"Sector: {saxutils.escape(p.get('sector_nombre') or '—')} · "
            f"Puesto: {saxutils.escape(p.get('puesto_nombre') or '—')}",
            styles["CapSub"],
        ),
        Spacer(1, 12),
    ]

    res = data["resumen"]
    kpi_data = [
        ["Cursos realizados", str(res["total_cursos_realizados"])],
        ["Certificaciones", str(res["total_certificaciones"])],
        ["Pendientes", str(res["total_pendientes"])],
        ["Sin planificar", str(res["total_sin_planificar"])],
    ]
    t = Table(kpi_data, colWidths=[8 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Cursos realizados", styles["CapH3"]))
    story.append(_tabla_cursos(data.get("cursos_realizados") or [], styles))

    story.append(Paragraph("Requisitos pendientes", styles["CapH3"]))
    story.append(_tabla_pendientes(data.get("pendientes") or [], styles))

    story.append(Paragraph("Planificación", styles["CapH3"]))
    story.append(_tabla_planes(data.get("planificacion") or [], styles))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generar_pdf_general(empresa_nombre: str, empresa_id: int) -> bytes:
    resumen = resumen_general_auditoria(empresa_id)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=1.2 * cm, rightMargin=1.2 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    styles = _base_styles()
    story = [
        Paragraph("Reporte general de capacitaciones", styles["CapTitle"]),
        Paragraph(
            f"{saxutils.escape(empresa_nombre)} · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["CapSub"],
        ),
        Spacer(1, 12),
        Paragraph(
            f"Personal activo: {resumen['participantes_activos']} · "
            f"Pendientes globales: {resumen['pendientes_globales']}",
            styles["CapSub"],
        ),
        Spacer(1, 12),
    ]

    iso_rows = [["Norma ISO", "Personas", "Requisitos", "Cumplidos", "Pendientes", "Vencidos", "% Cumplimiento"]]
    for codigo, r in resumen.get("normas_iso", {}).items():
        iso_rows.append([
            f"ISO {codigo}",
            str(r.get("personas_evaluadas", 0)),
            str(r.get("requisitos_total", 0)),
            str(r.get("cumplidos", 0)),
            str(r.get("pendientes", 0)),
            str(r.get("vencidos", 0)),
            f"{r.get('cumplimiento_pct', 0)}%",
        ])
    if len(iso_rows) > 1:
        t = Table(iso_rows, repeatRows=1)
        t.setStyle(_table_style_header())
        story.append(t)
    else:
        story.append(Paragraph("<i>Sin requisitos ISO configurados</i>", styles["CapCell"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generar_pdf_iso(empresa_nombre: str, empresa_id: int, norma: str) -> bytes:
    data = reporte_iso(empresa_id, norma)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=1 * cm, rightMargin=1 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    styles = _base_styles()
    res = data["resumen"]
    story = [
        Paragraph(f"Auditoría {saxutils.escape(data['titulo'])}", styles["CapTitle"]),
        Paragraph(
            f"{saxutils.escape(empresa_nombre)} · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["CapSub"],
        ),
        Spacer(1, 8),
        Paragraph(
            f"Cumplimiento: {res['cumplimiento_pct']}% · Personas: {res['personas_evaluadas']} · "
            f"Requisitos: {res['requisitos_total']} (cumplidos {res['cumplidos']}, pendientes {res['pendientes']}, vencidos {res['vencidos']})",
            styles["CapSub"],
        ),
        Spacer(1, 10),
    ]

    for persona in data.get("personas") or []:
        story.append(Paragraph(
            f"<b>{saxutils.escape(persona['nombre'])}</b> — Legajo {saxutils.escape(persona.get('legajo') or '—')} "
            f"({persona['cumplimiento_pct']}%)",
            styles["CapH3"],
        ))
        rows = [["Código", "Requisito", "Estado", "Vigencia", "Evidencia"]]
        for req in persona.get("requisitos") or []:
            vig = req.get("vigente_hasta") or req.get("fecha_vencimiento") or "—"
            evid = "Sí" if req.get("tiene_certificado") or req.get("tiene_documento") else "No"
            rows.append([
                req.get("codigo") or "—",
                req.get("nombre") or "—",
                _ESTADO_LABELS.get(req.get("estado"), req.get("estado")),
                vig,
                evid,
            ])
        t = Table(rows, colWidths=[2.5 * cm, 7 * cm, 3 * cm, 3 * cm, 2 * cm], repeatRows=1)
        t.setStyle(_table_style_header())
        story.append(t)
        story.append(Spacer(1, 8))

    if not data.get("personas"):
        story.append(Paragraph("<i>No hay personas con requisitos para esta norma.</i>", styles["CapCell"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def _tabla_cursos(cursos, styles):
    if not cursos:
        return Paragraph("<i>Sin cursos realizados</i>", styles["CapCell"])
    rows = [["Curso", "Fecha", "Nota", "Vigente hasta", "Cert."]]
    for c in cursos:
        rows.append([
            c.get("curso_nombre") or "—",
            c.get("fecha_realizacion") or "—",
            str(c.get("nota") if c.get("nota") is not None else "—"),
            c.get("vigente_hasta") or "—",
            "Sí" if c.get("tiene_certificado") else "No",
        ])
    t = Table(rows, colWidths=[6 * cm, 2.5 * cm, 1.5 * cm, 2.5 * cm, 1.5 * cm], repeatRows=1)
    t.setStyle(_table_style_header())
    return t


def _tabla_pendientes(items, styles):
    if not items:
        return Paragraph("<i>Sin pendientes</i>", styles["CapCell"])
    rows = [["Nombre", "Tipo", "Obligatorio", "Origen"]]
    for x in items:
        rows.append([
            x.get("nombre") or "—",
            x.get("tipo") or "—",
            "Sí" if x.get("obligatorio") else "No",
            x.get("origen_requisito") or "—",
        ])
    t = Table(rows, colWidths=[6 * cm, 2.5 * cm, 2 * cm, 2.5 * cm], repeatRows=1)
    t.setStyle(_table_style_header())
    return t


def _tabla_planes(planes, styles):
    if not planes:
        return Paragraph("<i>Sin planificación</i>", styles["CapCell"])
    rows = [["Curso", "Fecha prevista", "Estado"]]
    for pl in planes:
        rows.append([
            pl.get("curso_nombre") or "—",
            pl.get("fecha_planificada") or "—",
            pl.get("estado") or "—",
        ])
    t = Table(rows, colWidths=[8 * cm, 3 * cm, 3 * cm], repeatRows=1)
    t.setStyle(_table_style_header())
    return t


def _table_style_header():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])
