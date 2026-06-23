"""Tests módulo objetivos estratégicos."""
from app.services.objetivo_service import cargar_plantilla_2026, crear_objetivo, listar_objetivos


def test_crear_objetivo(app):
    with app.app_context():
        from app.models.usuario import Usuario

        eid = Usuario.query.first().empresa_id
        obj = crear_objetivo(
            eid,
            nombre="Incrementar ventas",
            descripcion="Aumentar la facturación en un 15% durante el período.",
            responsable_texto="Gerencia Comercial",
        )
        assert obj.codigo == "OE-01"
        assert len(listar_objetivos(eid)) == 1


def test_cargar_plantilla_2026(app):
    with app.app_context():
        from app.models.usuario import Usuario

        eid = Usuario.query.first().empresa_id
        n = cargar_plantilla_2026(eid)
        assert n == 10
        objs = listar_objetivos(eid)
        assert len(objs) == 10
        assert objs[0].codigo == "OE-01"
        assert objs[9].codigo == "OE-10"


def test_objetivos_index(auth_client):
    r = auth_client.get("/objetivos/")
    assert r.status_code == 200
    assert b"Cargar objetivos 2026" in r.data
