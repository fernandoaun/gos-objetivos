from gos.modulos.objetivos.models.objetivo import Objetivo
from gos.modulos.objetivos.services import kpi_service, objetivo_service, reportes_service


def _seed(app):
    with app.app_context():
        from gos.models import Empresa

        emp = Empresa.query.first()
        objetivo_service.crear_objetivo(
            emp.id,
            nombre="Objetivo estratégico 01",
            descripcion="Descripción del objetivo estratégico número uno.",
        )
        objetivo_service.crear_objetivo(
            emp.id,
            nombre="Objetivo estratégico 02",
            descripcion="Descripción del objetivo estratégico número dos.",
        )
        kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-01-01",
            indicador="KPI en meta",
            meta_2026="10",
            valores_mes={"1": 12},
        )
        kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-01-02",
            indicador="KPI fuera",
            meta_2026="10",
            valores_mes={"1": 5},
        )
        kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-02-01",
            indicador="KPI sin datos",
            meta_2026="10",
        )
        return emp.id


def test_vista_detalle_filtros(app):
    empresa_id = _seed(app)
    with app.app_context():
        informe = reportes_service.generar_informe_cumplimiento(empresa_id)

        vista_en_meta = reportes_service.preparar_vista_detalle(informe, "en-meta")
        assert vista_en_meta.total == 1
        assert vista_en_meta.hay_datos is True
        assert len(vista_en_meta.grupos[0].kpis) == 1

        vista_fuera = reportes_service.preparar_vista_detalle(informe, "fuera-meta")
        assert vista_fuera.total == 1

        vista_sin = reportes_service.preparar_vista_detalle(informe, "sin-datos")
        assert vista_sin.total == 1

        vista_obj = reportes_service.preparar_vista_detalle(informe, "objetivos-cumplimiento")
        assert vista_obj.total == 2
        assert vista_obj.hay_datos is True


def test_dashboard_detalle_routes(auth_client, app):
    _seed(app)
    for filtro in reportes_service.DASHBOARD_FILTROS:
        r = auth_client.get(f"/gos/objetivos/dashboard/detalle/{filtro}")
        assert r.status_code == 200
        assert b"Volver al dashboard" in r.data

    r404 = auth_client.get("/gos/objetivos/dashboard/detalle/no-existe")
    assert r404.status_code == 404
