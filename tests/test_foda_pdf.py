"""Tests exportación PDF FODA."""
from types import SimpleNamespace

from gos.modulos.objetivos.services.foda_pdf_export import generar_pdf_foda


def test_generar_pdf_foda_bytes():
    matriz = {
        "F": [SimpleNamespace(codigo="F-001", descripcion="Equipo & calidad <100%")],
        "O": [SimpleNamespace(codigo="O-001", descripcion="Mercado regional")],
        "D": [SimpleNamespace(codigo="D-001", descripcion="Digitalización")],
        "A": [SimpleNamespace(codigo="A-001", descripcion="Competencia")],
    }
    pdf = generar_pdf_foda("GOS Test", matriz)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500
