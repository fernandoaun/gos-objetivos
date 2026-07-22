import pytest

from gos.modulos.vacaciones import storage
from gos.modulos.vacaciones.models import Registro, Vacacion


@pytest.fixture(autouse=True)
def vacaciones_db(app):
    with app.app_context():
        storage.reset_for_tests()
        yield
        storage.reset_for_tests()


def test_vacaciones_health_requires_auth(client):
    r = client.get("/gos/vacaciones/api/health")
    assert r.status_code == 302
    assert "/auth/login" in r.location


def test_vacaciones_health_ok(auth_client):
    r = auth_client.get("/gos/vacaciones/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


def test_vacaciones_shell(auth_client):
    r = auth_client.get("/gos/vacaciones/")
    assert r.status_code == 200
    assert b"vac-frame" in r.data


def test_vacaciones_app(auth_client):
    r = auth_client.get("/gos/vacaciones/app/")
    assert r.status_code == 200
    assert b"Vacaciones Adeudadas" in r.data


def test_vacaciones_deuda_empty(auth_client):
    r = auth_client.get("/gos/vacaciones/api/vacaciones/deuda")
    assert r.status_code == 200
    assert r.get_json() == []


def test_vacaciones_dashboard_lists(auth_client, app):
    with app.app_context():
        from datetime import date

        from gos.extensions import db

        db.session.add(
            Registro(fecha=date(2025, 6, 1), empleado="Ana Test", sector="IT", vacaciones=0)
        )
        db.session.add(
            Vacacion(
                legajo=1,
                empleado="Ana Test",
                sector="IT",
                anio=2025,
                dias_disponibles=14,
                dias_tomados=5,
                dias_pendientes=9,
            )
        )
        db.session.commit()

    r = auth_client.get("/gos/vacaciones/api/dashboard/años")
    assert r.status_code == 200
    assert 2025 in r.get_json()

    r = auth_client.get("/gos/vacaciones/api/dashboard/sectores")
    assert r.status_code == 200
    assert "IT" in r.get_json()

    r = auth_client.get("/gos/vacaciones/api/dashboard/empleados")
    assert r.status_code == 200
    assert "Ana Test" in r.get_json()


def test_vacaciones_import_excel(auth_client):
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TOTAL"
    ws.append([
        "fecha", "empleado", "sector", "servicio", "centro", "situacion",
        "total_horas", "hs_viaje", "hs50", "hs_noc", "hs_noc50", "hs100",
        "viandas", "v_desayuno", "d_normales", "ausente", "fr_trabajados",
        "feriados", "enfermedad", "traslado", "vacaciones", "licencia",
        "suspension", "accidente", "francos_comp",
    ])
    ws.append([
        "2025-06-01", "Pedro Test", "RRHH", "", "", "", 8, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0,
    ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    r = auth_client.post(
        "/gos/vacaciones/api/importar/excel",
        data={"file": (buf, "test.xlsx")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["detalle"]["registros"] == 1


def test_vacaciones_import_planilla_archivo_actualizado(auth_client, app):
    """Importa el formato real: una hoja tipo planilla (sin TOTAL)."""
    import io
    from datetime import date, datetime

    import openpyxl
    from openpyxl.comments import Comment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hoja1"
    ws.append([
        "N° Legajo", "VACACIONES ", None, None, "Antigüedad ",
        "VACACIONES  2023", None, None, "Antigüedad",
        "VACACIONES  2024", None, None, "Antigüedad",
        "VACACIONES 2025", None, None,
    ])
    ws.append([
        None, "Empleado", "Fecha ingreso", "Sector", None,
        "Días Disponibles", "Días tomados", "Dias pendientes", None,
        "Días disponibles", "Días tomados", "Dias pendientes",
        datetime(2025, 12, 31), "Días Disponibles", "Días tomados", "Dias pendientes",
    ])
    ws.append([
        None, None, None, None, datetime(2023, 12, 31),
        None, None, None, datetime(2024, 12, 31),
        None, None, None, None, None, None, None,
    ])
    ws.append([
        43, "Alias, Fernando Javier", datetime(2007, 1, 1), "Operaciones",
        16, 28, 28, 0, 17, 28, 11, 17, 18, 28, None, 28,
        "Baja 2026", "Nota R test",
    ])
    ws.append([
        79, "Araneda, Ana Romina", datetime(2008, 1, 7), "Operaciones",
        15, 28, 28, 0, 16, 28, 28, 0, 16, 28, 3, 25,
        None, None,
    ])
    # Fórmula de suma en "Días tomados" (antes se leía como 0).
    ws["G4"] = "=SUM(7,21)"
    ws["O5"] = "=7+3+5"
    # Comentarios (triángulo rojo) en Días tomados 2023 (G) y 2025 (O)
    ws["G4"].comment = Comment("Tester:\n(7) 01/01 al 07/01/2023", "Tester")
    ws["O5"].comment = Comment("Tester:\n(3) 01-05-26 al 03-05-26", "Tester")
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    r = auth_client.post(
        "/gos/vacaciones/api/importar/excel",
        data={"file": (buf, "Archivo de Vacaciones-Actualizado.xlsx")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["detalle"]["vacaciones"] == 6  # 2 empleados × 3 años
    assert data["detalle"]["registros"] == 0

    with app.app_context():
        from gos.extensions import db

        rows = db.session.query(Vacacion).order_by(Vacacion.empleado, Vacacion.anio).all()
        assert len(rows) == 6
        ana_2025 = next(r for r in rows if r.empleado.startswith("Araneda") and r.anio == 2025)
        assert ana_2025.dias_disponibles == 28
        assert ana_2025.dias_tomados == 15  # =7+3+5
        assert ana_2025.dias_pendientes == 25
        assert ana_2025.fecha_ingreso == date(2008, 1, 7)
        assert ana_2025.comentario == "(3) 01-05-26 al 03-05-26"

        alias_2023 = next(r for r in rows if r.empleado.startswith("Alias") and r.anio == 2023)
        assert alias_2023.dias_tomados == 28  # =SUM(7,21)
        assert alias_2023.comentario == "(7) 01/01 al 07/01/2023"
        assert alias_2023.nota_q == "Baja 2026"
        assert alias_2023.nota_r == "Nota R test"

    r = auth_client.get("/gos/vacaciones/api/vacaciones/deuda")
    assert r.status_code == 200
    deuda = r.get_json()
    assert len(deuda) == 6
    assert any(d["dias_pendientes"] == 17 for d in deuda)
    alias_api = next(d for d in deuda if d["empleado"].startswith("Alias") and d["anio"] == 2023)
    assert alias_api["fecha_ingreso"] == "2007-01-01"
    assert alias_api["comentario"] == "(7) 01/01 al 07/01/2023"
    assert alias_api["nota_q"] == "Baja 2026"
    assert alias_api["nota_r"] == "Nota R test"

    r = auth_client.get("/gos/vacaciones/api/dashboard/sectores")
    assert "Operaciones" in r.get_json()

    r = auth_client.get("/gos/vacaciones/api/dashboard/años")
    assert r.get_json() == [2023, 2024, 2025]


def _xlsx_total(rows):
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TOTAL"
    ws.append([
        "fecha", "empleado", "sector", "servicio", "centro", "situacion",
        "total_horas", "hs_viaje", "hs50", "hs_noc", "hs_noc50", "hs100",
        "viandas", "v_desayuno", "d_normales", "ausente", "fr_trabajados",
        "feriados", "enfermedad", "traslado", "vacaciones", "licencia",
        "suspension", "accidente", "francos_comp",
    ])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def test_tot_hs_shell_and_app(auth_client):
    r = auth_client.get("/gos/vacaciones/tot-hs")
    assert r.status_code == 200
    assert b"vac-frame" in r.data
    assert b"view=tot_hs" in r.data or b"tot_hs" in r.data

    r = auth_client.get("/gos/vacaciones/app/?view=tot_hs")
    assert r.status_code == 200
    assert b"Tot Hs." in r.data
    assert b"view-tot-hs" in r.data


def test_tot_hs_import_merge_and_overwrite(auth_client, app):
    """Fechas nuevas se suman; (fecha, empleado) repetidos se pisan sin duplicar."""
    from datetime import date

    buf1 = _xlsx_total([
        ["2025-06-01", "Pedro Test", "RRHH", "", "", "", 8, 0, 1, 0, 0, 0,
         0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ["2025-06-02", "Pedro Test", "RRHH", "", "", "", 8, 0, 0, 0, 0, 0,
         0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ])
    r = auth_client.post(
        "/gos/vacaciones/api/importar/total",
        data={"file": (buf1, "tot1.xlsx")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["detalle"]["registros"] == 2
    assert data["detalle"]["registros_nuevos"] == 2

    # Segundo archivo: actualiza 01/06 y agrega 03/06
    buf2 = _xlsx_total([
        ["2025-06-01", "Pedro Test", "RRHH", "", "", "", 10, 0, 2, 0, 0, 0,
         0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ["2025-06-03", "Pedro Test", "RRHH", "", "", "", 8, 0, 0, 0, 0, 0,
         0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ])
    r = auth_client.post(
        "/gos/vacaciones/api/importar/total",
        data={"file": (buf2, "tot2.xlsx")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["detalle"]["registros"] == 2
    assert data["detalle"]["registros_nuevos"] == 1
    assert data["detalle"]["registros_actualizados"] == 1

    with app.app_context():
        from gos.extensions import db

        regs = (
            db.session.query(Registro)
            .filter_by(empleado="Pedro Test")
            .order_by(Registro.fecha)
            .all()
        )
        assert len(regs) == 3  # sin duplicar el 01/06
        assert regs[0].fecha == date(2025, 6, 1)
        assert regs[0].total_horas == 10  # pisado
        assert regs[0].hs50 == 2
        assert regs[1].fecha == date(2025, 6, 2)
        assert regs[1].total_horas == 8  # conservado
        assert regs[2].fecha == date(2025, 6, 3)

    r = auth_client.get("/gos/vacaciones/api/tot-hs/resumen?anios=2025")
    assert r.status_code == 200
    resumen = r.get_json()
    assert resumen["registros"] == 3
    assert resumen["total_horas"] == 26
    assert resumen["personas"] == 1

    r = auth_client.get("/gos/vacaciones/api/tot-hs/por-empleado?anios=2025")
    assert r.status_code == 200
    empleados = r.get_json()
    assert len(empleados) == 1
    assert empleados[0]["empleado"] == "Pedro Test"
    assert empleados[0]["total_horas"] == 26

    r = auth_client.get("/gos/vacaciones/api/tot-hs/meta")
    assert r.status_code == 200
    meta = r.get_json()
    assert meta["total_registros"] == 3
    assert 2025 in meta["anios"]


def test_tot_hs_import_requires_total_sheet(auth_client):
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    wb.active.title = "OTRA"
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    r = auth_client.post(
        "/gos/vacaciones/api/importar/total",
        data={"file": (buf, "sin_total.xlsx")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 500
    assert "TOTAL" in r.get_json()["error"]
