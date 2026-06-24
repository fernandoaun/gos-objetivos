"""Tests matriz DAFO 2×2 (una tarea por cuadrante)."""
from types import SimpleNamespace

from gos.modulos.objetivos.services.foda_dafo_service import (
    CELDA_MATRIZ,
    generar_matriz_dafo,
    guardar_tarea_cuadrante,
    total_estrategias_dafo,
)


def _item(tipo, codigo, descripcion, orden=0, item_id=0):
    return SimpleNamespace(
        tipo=tipo, codigo=codigo, descripcion=descripcion, orden=orden, id=item_id
    )


def test_cuatro_cuadrantes_una_tarea_cada_uno():
    matriz = {
        "F": [_item("F", "F-001", "Equipo")],
        "O": [_item("O", "O-001", "Mercado")],
        "D": [_item("D", "D-001", "Digital")],
        "A": [_item("A", "A-001", "Competencia")],
    }
    dafo = generar_matriz_dafo(matriz)
    assert total_estrategias_dafo(dafo) == 4
    assert dafo["FO"]["cuadrante"].activo
    assert dafo["FO"]["cuadrante"].tarea == ""
    assert dafo["FO"]["cuadrante"].tipo == "FO"


def test_cuadrante_inactivo_sin_f_o():
    matriz = {"F": [_item("F", "F-001", "X")], "O": [], "D": [], "A": []}
    dafo = generar_matriz_dafo(matriz)
    assert not dafo["FO"]["cuadrante"].activo
    assert total_estrategias_dafo(dafo) == 0


def test_guardar_una_tarea_por_cuadrante(app):
    with app.app_context():
        from gos.modulos.objetivos.models.foda import DafoTarea
        from gos.models.usuario import Usuario

        u = Usuario.query.first()
        eid = u.empresa_id
        matriz = {
            "F": [_item("F", "F-001", "Fortaleza")],
            "O": [_item("O", "O-001", "Oportunidad")],
            "D": [],
            "A": [],
        }
        generar_matriz_dafo(matriz, empresa_id=eid)
        guardar_tarea_cuadrante(eid, "FO", "Única tarea estratégica FO")
        dafo = generar_matriz_dafo(matriz, empresa_id=eid)
        assert dafo["FO"]["cuadrante"].tarea == "Única tarea estratégica FO"
        row = DafoTarea.query.filter_by(
            empresa_id=eid, tipo="FO", origen_a_codigo=CELDA_MATRIZ
        ).one()
        assert row.tarea == "Única tarea estratégica FO"
