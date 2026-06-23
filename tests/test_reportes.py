from app.models.objetivo import Objetivo
from app.services import kpi_service, objetivo_service, reportes_service


def _seed_objetivos(empresa_id: int, n: int = 2) -> None:
    for i in range(1, n + 1):
        objetivo_service.crear_objetivo(
            empresa_id,
            nombre=f"Objetivo estratégico {i:02d}",
            descripcion=f"Descripción del objetivo estratégico número {i}.",
        )


def test_informe_cumplimiento(app):
    with app.app_context():
        from app.models import Empresa

        emp = Empresa.query.first()
        _seed_objetivos(emp.id, 2)

        objetivos = Objetivo.query.filter_by(empresa_id=emp.id, activo=True).all()
        oe01 = next(o for o in objetivos if o.codigo == "OE-01")
        oe02 = next(o for o in objetivos if o.codigo == "OE-02")

        kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-01-01",
            indicador="KPI cumplido OE01",
            meta_2026="10",
            valores_mes={"1": 12},
        )
        kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-01-02",
            indicador="KPI fuera OE01",
            meta_2026="10",
            valores_mes={"1": 5},
        )
        kpi_service.crear_kpi(
            emp.id,
            codigo="KPI-02-01",
            indicador="KPI cumplido OE02",
            meta_2026="20",
            valores_mes={"1": 25},
        )

        informe = reportes_service.generar_informe_cumplimiento(emp.id)

        assert informe.total_objetivos == 2
        assert informe.total_kpis == 3
        assert informe.kpis_cumplidos == 2
        assert informe.kpis_fuera == 1
        assert informe.pct_kpis_cumplidos == 66.7

        oe01_row = next(o for o in informe.objetivos if o.codigo == oe01.codigo)
        oe02_row = next(o for o in informe.objetivos if o.codigo == oe02.codigo)

        assert oe01_row.total_kpis == 2
        assert oe01_row.kpis_cumplidos == 1
        assert oe01_row.pct_cumplimiento == 50.0
        assert oe01_row.cumplido is False

        assert oe02_row.total_kpis == 1
        assert oe02_row.cumplido is True

        assert informe.objetivos_cumplidos == 1
        assert informe.objetivos_con_kpis == 2
        assert informe.pct_objetivos_cumplidos == 50.0


def test_reportes_route(auth_client):
    r = auth_client.get("/reportes/")
    assert r.status_code == 200
    assert b"Informe de cumplimiento" in r.data
    assert b"Objetivos estrat" in r.data
