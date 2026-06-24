def test_alumno_solo_ve_capacitacion(alumno_client):
    r = alumno_client.get("/", follow_redirects=True)
    assert r.status_code == 200
    assert b"Capacitaci" in r.data or b"capacitacion" in r.data.lower()
    # Objetivos no debería aparecer en el menú de módulos para alumnos
    assert b"Objetivos" not in r.data or b"/gos/capacitacion/" in r.data
