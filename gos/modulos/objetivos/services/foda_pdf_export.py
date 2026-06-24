"""Exporta la matriz FODA a PDF."""
import io
import xml.sax.saxutils as saxutils
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from gos.modulos.objetivos.models.foda import FODA_LABELS
_QUAD_COLORS = {
    "F": colors.HexColor("#e8f5dc"),
    "D": colors.HexColor("#ececec"),
    "O": colors.HexColor("#fdf6dc"),
    "A": colors.HexColor("#e5e5e5"),
}
_HEADER_COLORS = {
    "F": colors.HexColor("#76B947"),
    "D": colors.HexColor("#808080"),
    "O": colors.HexColor("#F9E29C"),
    "A": colors.HexColor("#5c5c5c"),
}


def generar_pdf_foda(empresa_nombre: str, matriz: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="FodaTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=6))
    styles.add(ParagraphStyle(name="FodaSub", parent=styles["Normal"], fontSize=10, textColor=colors.grey))
    styles.add(ParagraphStyle(name="FodaQuadTitle", parent=styles["Normal"], fontSize=11, leading=14))
    styles.add(ParagraphStyle(name="FodaItem", parent=styles["Normal"], fontSize=9, leading=12, spaceAfter=4))
    styles.add(ParagraphStyle(name="FodaAxis", parent=styles["Normal"], fontSize=8, alignment=1, textColor=colors.grey))

    story = [
        Paragraph("Análisis FODA", styles["FodaTitle"]),
        Paragraph(
            f"{saxutils.escape(empresa_nombre)} · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles["FodaSub"],
        ),
        Spacer(1, 12),
        Table(
            [["", "Factores positivos", "Factores negativos"]],
            colWidths=[2.2 * cm, 12 * cm, 12 * cm],
            style=TableStyle([
                ("FONTNAME", (1, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#76B947")),
                ("TEXTCOLOR", (2, 0), (2, 0), colors.HexColor("#808080")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ]),
        ),
        Spacer(1, 6),
    ]

    def make_inner_table(tipo):
        items = matriz.get(tipo, [])
        data = [[Paragraph(
            f"<b><font color='white'>{FODA_LABELS[tipo]}</font></b>",
            styles["FodaQuadTitle"],
        )]]
        if items:
            for it in items:
                desc = saxutils.escape(it.descripcion)
                line = f"<b>{it.codigo}</b> — {desc}"
                data.append([Paragraph(line, styles["FodaItem"])])
        else:
            data.append([Paragraph("<i>Sin ítems</i>", styles["FodaItem"])])

        t = Table(data, colWidths=[11.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_COLORS[tipo]),
            ("BACKGROUND", (0, 1), (-1, -1), _QUAD_COLORS[tipo]),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    matrix_table = Table(
        [
            [Paragraph("", styles["Normal"]), make_inner_table("F"), make_inner_table("D")],
            [Paragraph("<b>Externo</b>", styles["FodaAxis"]), make_inner_table("O"), make_inner_table("A")],
        ],
        colWidths=[2.2 * cm, 12.2 * cm, 12.2 * cm],
        rowHeights=[None, None],
    )
    matrix_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(matrix_table)
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "<font size='8' color='#64748b'>GOS Objetivos — Planeamiento Estratégico</font>",
        styles["FodaSub"],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
