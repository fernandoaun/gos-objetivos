import pytest

from gos.modulos.objetivos.services.foda_service import crear_item_manual, eliminar_item, renumerar_codigos_activos


def test_codigos_empiezan_en_001(app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        eid = emp.id

        crear_item_manual(eid, "F", "Fortaleza uno")
        crear_item_manual(eid, "F", "Fortaleza dos")
        crear_item_manual(eid, "O", "Oportunidad uno")

        from gos.modulos.objetivos.models import FodaItem

        f_items = (
            FodaItem.query.filter_by(empresa_id=eid, tipo="F", activo=True)
            .order_by(FodaItem.codigo)
            .all()
        )
        assert [i.codigo for i in f_items] == ["F-001", "F-002"]

        o_items = FodaItem.query.filter_by(empresa_id=eid, tipo="O", activo=True).all()
        assert o_items[0].codigo == "O-001"

        eliminar_item(eid, f_items[0].id)
        f_items = (
            FodaItem.query.filter_by(empresa_id=eid, tipo="F", activo=True)
            .order_by(FodaItem.codigo)
            .all()
        )
        assert [i.codigo for i in f_items] == ["F-001"]
