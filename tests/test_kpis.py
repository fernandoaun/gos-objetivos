from gos.modulos.objetivos.models.kpi import KpiIndicador
from gos.modulos.objetivos.services import kpi_service


def test_crear_y_actualizar_kpi(app):
    with app.app_context():
        from gos.extensions import db
        from gos.models import Empresa

        emp = Empresa.query.first()
        if not emp:
            emp = Empresa(nombre="KPI Test", activa=True)
            db.session.add(emp)
            db.session.commit()

        kpi = kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-99-01",
            indicador="Indicador de prueba",
            meta_2026="100",
            tipo_agregacion="suma",
            valores_mes={"1": 10, "2": 20},
        )
        assert kpi.id is not None
        assert kpi.numero == 1
        assert kpi.tipo_agregacion == "suma"

        metricas = kpi_service.calcular_metricas(kpi)
        assert metricas["agregado"] == 30

        kpi_service.actualizar_kpi(
            emp.id,
            kpi.id,
            indicador="Indicador actualizado",
            meta_2026="200",
            tipo_agregacion="ultimo",
            valores_mes={"1": 50, "2": 80},
        )
        actualizado = KpiIndicador.query.get(kpi.id)
        assert actualizado.indicador == "Indicador actualizado"
        assert actualizado.meta_2026_num == 200
        assert actualizado.tipo_agregacion == "ultimo"
        assert kpi_service.calcular_metricas(actualizado)["agregado"] == 80

        kpi2 = kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-99-02",
            indicador="Segundo indicador",
        )
        assert kpi2.numero == 2

        codigo = kpi_service.eliminar_kpi(emp.id, kpi.id)
        assert codigo == "KPI-99-01"
        assert KpiIndicador.query.get(kpi.id).activo is False


def test_calcular_metricas_por_tipo(app):
    with app.app_context():
        from gos.extensions import db
        from gos.models import Empresa

        emp = Empresa.query.first()
        if not emp:
            emp = Empresa(nombre="KPI Tipos", activa=True)
            db.session.add(emp)
            db.session.commit()

        casos = [
            ("suma", {"1": 40, "2": 35}, 75, "100", 0.75),
            ("cumplimiento", {"1": 80, "2": 95}, 95, "90", 95 / 90),
            ("promedio", {"1": 80, "2": 100}, 90, "95", 90 / 95),
            ("ultimo", {"1": 50, "2": 120}, 120, "100", 1.2),
        ]
        for idx, (tipo, meses, agregado, meta, avance) in enumerate(casos, start=1):
            kpi = kpi_service.crear_kpi(
                emp.id,
                codigo=f"KPI-T-{idx:02d}",
                indicador=f"Tipo {tipo}",
                meta_2026=meta,
                tipo_agregacion=tipo,
                valores_mes=meses,
            )
            metricas = kpi_service.calcular_metricas(kpi)
            assert metricas["agregado"] == agregado
            assert metricas["avance"] == avance
            assert metricas["estado"] == ("En meta" if avance >= 1 else "Fuera de meta")


def test_kpi_meta_cero_con_valor_cero(app):
    """Meta 0 + valor 0 = cumplido (ej. incidentes ambientales)."""
    with app.app_context():
        from gos.extensions import db
        from gos.models import Empresa

        emp = Empresa.query.first()
        if not emp:
            emp = Empresa(nombre="KPI Meta Cero", activa=True)
            db.session.add(emp)
            db.session.commit()

        kpi = kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-Z-01",
            indicador="Incidentes ambientales",
            meta_2026="0",
            tipo_agregacion="suma",
            valores_mes={"1": 0, "2": 0, "3": 0, "4": 0},
        )
        metricas = kpi_service.calcular_metricas(kpi)
        assert metricas["agregado"] == 0
        assert metricas["avance"] == 1.0
        assert metricas["estado"] == "En meta"


def test_kpi_menor_es_mejor(app):
    """Consumo / no conformidades: valor por debajo de la meta = en meta."""
    with app.app_context():
        from gos.extensions import db
        from gos.models import Empresa

        emp = Empresa.query.first()
        if not emp:
            emp = Empresa(nombre="KPI Menor", activa=True)
            db.session.add(emp)
            db.session.commit()

        reduccion = kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-Z-02",
            indicador="Reduccion Consumo energético por operación",
            meta_2026="0.1",
            tipo_agregacion="promedio",
            valores_mes={"1": 0, "2": 0, "3": 0, "4": 0},
        )
        assert kpi_service.calcular_metricas(reduccion)["estado"] == "En meta"

        nc = kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-Z-03",
            indicador="No conformidades",
            meta_2026="2",
            tipo_agregacion="promedio",
            valores_mes={"1": 0, "2": 0, "3": 0, "4": 1},
        )
        assert kpi_service.calcular_metricas(nc)["estado"] == "En meta"


def test_kpi_routes_post(auth_client):
    client = auth_client
    r = client.post(
        "/gos/objetivos/kpis/nuevo",
        data={
            "codigo": "KPI-88-01",
            "indicador": "Desde test HTTP",
            "meta_2026": "10",
            "tipo_agregacion": "promedio",
            "mes_1": "3",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"KPI agregado" in r.data or b"KPI-88-01" in r.data

    with client.application.app_context():
        kpi = KpiIndicador.query.filter_by(codigo="KPI-88-01", activo=True).first()
        assert kpi is not None

    r2 = client.post(
        f"/gos/objetivos/kpis/{kpi.id}/actualizar",
        data={
            "indicador": "Actualizado HTTP",
            "meta_2026": "20",
            "tipo_agregacion": "suma",
            "mes_1": "5",
        },
        follow_redirects=True,
    )
    assert r2.status_code == 200
    assert b"guardado" in r2.data

    r_tipo = client.post(
        f"/gos/objetivos/kpis/{kpi.id}/tipo",
        data={"tipo_agregacion": "ultimo"},
        follow_redirects=True,
    )
    assert r_tipo.status_code == 200
    with client.application.app_context():
        assert KpiIndicador.query.filter_by(codigo="KPI-88-01", activo=True).first().tipo_agregacion == "ultimo"

    r3 = client.get(f"/gos/objetivos/kpis/?ver={kpi.id}")
    assert r3.status_code == 200
    assert b"kpi-row-highlighted" in r3.data
    assert b"kpi-row-editing" not in r3.data
